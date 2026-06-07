import Foundation
import Darwin
import os

/// Locates and runs bundled or host ``webaudit`` / ``webaudit-docker``; streams combined stdout/stderr.
final class ScanRunner {
    static let outputRoot = FileManager.default.homeDirectoryForCurrentUser
        .appendingPathComponent("Documents/WebAudit", isDirectory: true)

    private static let bundledEngineRelativePath = "Engine/bin/webaudit"
    private static let bundledPlaywrightBrowsersRelativePath = "Engine/playwright-browsers"
    private static let enginePolicyPlistKey = "WEBAUDITEnginePolicy"

    private let lastRunMarker = ".webaudit-last-run"

    private struct ProcessSlot {
        var activeProcess: Process?
        var userCancelled = false
    }

    private let processSlot = OSAllocatedUnfairLock(initialState: ProcessSlot())

    func terminateScan() {
        let process = processSlot.withLock { slot -> Process? in
            slot.userCancelled = true
            return slot.activeProcess
        }

        guard let process, process.isRunning else { return }
        process.terminate()

        let pid = process.processIdentifier
        DispatchQueue.global(qos: .utility).asyncAfter(deadline: .now() + 3) {
            guard process.isRunning else { return }
            kill(pid, SIGKILL)
        }
    }

    private func setActiveProcess(_ process: Process) {
        processSlot.withLock { $0.activeProcess = process }
    }

    private func clearActiveProcess() {
        processSlot.withLock { $0.activeProcess = nil }
    }

    private func wasUserCancelled() -> Bool {
        processSlot.withLock { $0.userCancelled }
    }

    private func prepareScan() throws -> ScanEngineInfo {
        try FileManager.default.createDirectory(at: Self.outputRoot, withIntermediateDirectories: true)
        processSlot.withLock { $0.userCancelled = false }

        let engine = detectEngine()
        guard engine.kind != .none else {
            throw ScanRunnerError.engineMissing(policy: Self.enginePolicy())
        }
        return engine
    }

    static func enginePolicy() -> EnginePolicy {
        if let raw = ProcessInfo.processInfo.environment["WEBAUDIT_ENGINE_POLICY"],
           let policy = EnginePolicy(rawValue: raw) {
            return policy
        }
        if let raw = Bundle.main.object(forInfoDictionaryKey: enginePolicyPlistKey) as? String,
           let policy = EnginePolicy(rawValue: raw) {
            return policy
        }
        if bundledEnginePath() != nil {
            return .bundledFirst
        }
        return .externalFirst
    }

    func detectEngine() -> ScanEngineInfo {
        let policy = Self.enginePolicy()
        let bundled = resolveBundledCandidates()
        let docker = resolveDockerWrapperCandidates()
        let cli = resolveWebauditCandidates()

        let ordered: [(String, ScanEngineInfo.Kind)]
        switch policy {
        case .bundledFirst:
            ordered = bundled + cli + docker
        case .externalFirst:
            ordered = docker + cli + bundled
        }

        for (path, kind) in ordered {
            if isRunnable(at: path) {
                return ScanEngineInfo(kind: kind, path: path, detail: engineDetail(for: kind))
            }
        }

        return ScanEngineInfo(
            kind: .none,
            path: "",
            detail: policy == .bundledFirst
                ? "Bundled scan engine missing from app Resources/Engine"
                : "Install webaudit-docker (see README) or webaudit on PATH"
        )
    }

    func runScan(url: String, onLine: @escaping (String) -> Void) async throws -> URL {
        let engine = try prepareScan()

        let process = Process()
        let pipe = Pipe()
        process.standardOutput = pipe
        process.standardError = pipe
        process.environment = Self.subprocessEnvironment(enginePath: engine.path)

        switch engine.kind {
        case .bundled, .webauditCLI, .webauditDocker:
            configureProcess(
                process,
                scriptPath: engine.path,
                arguments: Self.scanProcessArguments(engineKind: engine.kind, url: url)
            )
        case .none:
            throw ScanRunnerError.engineMissing(policy: Self.enginePolicy())
        }

        let lineBuffer = OutputLineBuffer()

        return try await withTaskCancellationHandler {
            try await withCheckedThrowingContinuation { continuation in
                let resume = ContinuationGuard(continuation)

                pipe.fileHandleForReading.readabilityHandler = { handle in
                    let chunk = handle.availableData
                    guard !chunk.isEmpty else { return }
                    lineBuffer.append(chunk, onLine: onLine)
                }

                process.terminationHandler = { [self] proc in
                    pipe.fileHandleForReading.readabilityHandler = nil
                    lineBuffer.drainTail(onLine: onLine)
                    if self.wasUserCancelled() {
                        resume.finishOnce(.failure(CancellationError()), clearProcess: self.clearActiveProcess)
                        return
                    }
                    if proc.terminationStatus != 0 {
                        resume.finishOnce(
                            .failure(ScanRunnerError.scanFailed(code: Int(proc.terminationStatus))),
                            clearProcess: self.clearActiveProcess
                        )
                        return
                    }
                    do {
                        let runDir = try self.resolveLatestRunDirectory()
                        resume.finishOnce(.success(runDir), clearProcess: self.clearActiveProcess)
                    } catch {
                        resume.finishOnce(.failure(error), clearProcess: self.clearActiveProcess)
                    }
                }

                setActiveProcess(process)
                do {
                    try process.run()
                } catch {
                    resume.finishOnce(.failure(error), clearProcess: clearActiveProcess)
                }
            }
        } onCancel: {
            self.terminateScan()
        }
    }

    func resolveLatestRunDirectory() throws -> URL {
        let marker = Self.outputRoot.appendingPathComponent(lastRunMarker)
        if let data = try? Data(contentsOf: marker),
           let raw = String(data: data, encoding: .utf8)?.trimmingCharacters(in: .whitespacesAndNewlines),
           !raw.isEmpty {
            let dir = URL(fileURLWithPath: raw, isDirectory: true)
            if FileManager.default.fileExists(atPath: dir.path) {
                return dir
            }
        }
        guard let entries = try? FileManager.default.contentsOfDirectory(
            at: Self.outputRoot,
            includingPropertiesForKeys: [.contentModificationDateKey],
            options: [.skipsHiddenFiles]
        ) else {
            throw ScanRunnerError.reportNotFound
        }
        let dirs = entries.filter { url in
            var isDir: ObjCBool = false
            return FileManager.default.fileExists(atPath: url.path, isDirectory: &isDir) && isDir.boolValue
        }
        guard let latest = dirs.max(by: { a, b in
            let da = (try? a.resourceValues(forKeys: [.contentModificationDateKey]).contentModificationDate) ?? .distantPast
            let db = (try? b.resourceValues(forKeys: [.contentModificationDateKey]).contentModificationDate) ?? .distantPast
            return da < db
        }) else {
            throw ScanRunnerError.reportNotFound
        }
        return latest
    }

    func loadVerdictSummary(from runDir: URL) -> String? {
        let jsonURL = runDir.appendingPathComponent("audit_run.json")
        guard let data = try? Data(contentsOf: jsonURL),
              let obj = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let scores = obj["scores"] as? [String: Any],
              let verdict = scores["verdict"] as? String,
              let hygiene = scores["hygiene"] as? Int,
              let exposure = scores["exposure"] as? Int else {
            return nil
        }
        return "\(verdict) · Hygiene \(hygiene) · Exposure \(exposure)"
    }

    /// Process arguments for ``runScan`` — public DMG, dev Docker, and host CLI pass ``--js`` and ``--api`` by default.
    static func scanProcessArguments(engineKind: ScanEngineInfo.Kind, url: String) -> [String] {
        switch engineKind {
        case .bundled, .webauditCLI:
            return [
                "scan", url,
                "-v",
                "--js",
                "--api",
                "--open", "none",
                "-o", outputRoot.path,
            ]
        case .webauditDocker:
            return [
                "--output-dir", "documents",
                "--open", "none",
                "-y",
                "scan", url,
                "-v",
                "--js",
                "--api",
            ]
        case .none:
            return []
        }
    }

    private static func bundledEnginePath() -> String? {
        guard let resources = Bundle.main.resourceURL else { return nil }
        let path = resources.appendingPathComponent(bundledEngineRelativePath).path
        return FileManager.default.isReadableFile(atPath: path) ? path : nil
    }

    private static func bundledPlaywrightBrowsersPath() -> String? {
        guard let resources = Bundle.main.resourceURL else { return nil }
        let path = resources.appendingPathComponent(bundledPlaywrightBrowsersRelativePath).path
        var isDir: ObjCBool = false
        guard FileManager.default.fileExists(atPath: path, isDirectory: &isDir), isDir.boolValue else {
            return nil
        }
        return path
    }

    private func resolveBundledCandidates() -> [(String, ScanEngineInfo.Kind)] {
        guard let path = Self.bundledEnginePath() else { return [] }
        return [(path, .bundled)]
    }

    private func resolveDockerWrapperCandidates() -> [(String, ScanEngineInfo.Kind)] {
        var paths: [String] = []
        let home = FileManager.default.homeDirectoryForCurrentUser.path
        paths.append("\(home)/.local/bin/webaudit-docker")
        paths.append("/usr/local/bin/webaudit-docker")
        if let env = ProcessInfo.processInfo.environment["WEBAUDIT_DOCKER_SCRIPT"],
           !env.isEmpty {
            paths.insert(env, at: 0)
        }
        if let repo = ProcessInfo.processInfo.environment["WEBAUDIT_REPO"] {
            paths.append("\(repo)/v2_python_core/scripts/webaudit-docker.sh")
        }
        if let fromShell = shellWhich("webaudit-docker") {
            paths.append(fromShell)
        }
        return paths.map { ($0, .webauditDocker) }
    }

    private func resolveWebauditCandidates() -> [(String, ScanEngineInfo.Kind)] {
        var paths: [String] = []
        let home = FileManager.default.homeDirectoryForCurrentUser.path
        paths.append("\(home)/.local/bin/webaudit")
        paths.append("/usr/local/bin/webaudit")
        if let venv = ProcessInfo.processInfo.environment["WEBAUDIT_VENV"] {
            paths.append("\(venv)/bin/webaudit")
        }
        if let repo = ProcessInfo.processInfo.environment["WEBAUDIT_REPO"] {
            paths.append("\(repo)/v2_python_core/.venv/bin/webaudit")
        }
        if let fromShell = shellWhich("webaudit") {
            paths.append(fromShell)
        }
        return paths.map { ($0, .webauditCLI) }
    }

    private func engineDetail(for kind: ScanEngineInfo.Kind) -> String {
        switch kind {
        case .bundled:
            return "Ready (inside app)"
        case .webauditDocker, .webauditCLI:
            return "Ready"
        case .none:
            return "Not found"
        }
    }

    /// GUI launches (Finder, Dock, Launchpad) get a minimal PATH. Terminal tools like
    /// `docker` and `webaudit-docker` live in Homebrew, Docker.app, or ~/.local/bin.
    private static func subprocessEnvironment(enginePath: String? = nil) -> [String: String] {
        var env = ProcessInfo.processInfo.environment
        let home = FileManager.default.homeDirectoryForCurrentUser.path
        var extraPaths = [
            "\(home)/.local/bin",
            "/opt/homebrew/bin",
            "/opt/homebrew/sbin",
            "/usr/local/bin",
            "/Applications/Docker.app/Contents/Resources/bin",
        ]
        if let enginePath {
            let engineBin = URL(fileURLWithPath: enginePath).deletingLastPathComponent().path
            extraPaths.insert(engineBin, at: 0)
        }
        if let bundled = bundledEnginePath() {
            let engineBin = URL(fileURLWithPath: bundled).deletingLastPathComponent().path
            extraPaths.insert(engineBin, at: 0)
        }
        let existing = env["PATH"] ?? "/usr/bin:/bin:/usr/sbin:/sbin"
        var seen = Set<String>()
        var parts: [String] = []
        for segment in extraPaths + existing.split(separator: ":").map(String.init) {
            guard !segment.isEmpty, seen.insert(segment).inserted else { continue }
            parts.append(segment)
        }
        env["PATH"] = parts.joined(separator: ":")
        if let browsers = bundledPlaywrightBrowsersPath() {
            env["PLAYWRIGHT_BROWSERS_PATH"] = browsers
        }
        return env
    }

    private func shellWhich(_ name: String) -> String? {
        let process = Process()
        let pipe = Pipe()
        process.executableURL = URL(fileURLWithPath: "/usr/bin/which")
        process.arguments = [name]
        process.standardOutput = pipe
        process.standardError = Pipe()
        process.environment = Self.subprocessEnvironment()
        do {
            try process.run()
            process.waitUntilExit()
        } catch {
            return nil
        }
        guard process.terminationStatus == 0 else { return nil }
        let data = pipe.fileHandleForReading.readDataToEndOfFile()
        let path = String(data: data, encoding: .utf8)?
            .trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        return path.isEmpty ? nil : path
    }

    private func isRunnable(at path: String) -> Bool {
        if FileManager.default.isExecutableFile(atPath: path) { return true }
        return path.hasSuffix(".sh") && FileManager.default.isReadableFile(atPath: path)
    }

    private func configureProcess(_ process: Process, scriptPath: String, arguments: [String]) {
        if FileManager.default.isExecutableFile(atPath: scriptPath) {
            process.executableURL = URL(fileURLWithPath: scriptPath)
            process.arguments = arguments
        } else if scriptPath.hasSuffix(".sh") {
            process.executableURL = URL(fileURLWithPath: "/bin/bash")
            process.arguments = [scriptPath] + arguments
        } else {
            process.executableURL = URL(fileURLWithPath: scriptPath)
            process.arguments = arguments
        }
        // Playwright's driver rejects invalid CWD when the app is launched from Finder/Dock.
        try? FileManager.default.createDirectory(at: Self.outputRoot, withIntermediateDirectories: true)
        process.currentDirectoryURL = Self.outputRoot
    }
}

enum ScanRunnerError: LocalizedError {
    case engineMissing(policy: EnginePolicy)
    case scanFailed(code: Int)
    case reportNotFound

    var errorDescription: String? {
        switch self {
        case .engineMissing(let policy):
            switch policy {
            case .bundledFirst:
                return """
                Scan engine missing from this app bundle.
                Reinstall Web Audit from the official .dmg, or contact support.
                """
            case .externalFirst:
                return """
                Scan engine not found. Install once:
                • Docker: webaudit-docker → ~/.local/bin (see v2_python_core/docs/docker_ci.md)
                • Or: pip install webaudit / dev venv with webaudit on PATH
                """
            }
        case .scanFailed(let code):
            return "Scan failed (exit \(code)). See log above."
        case .reportNotFound:
            return "Scan finished but no report folder was found in ~/Documents/WebAudit."
        }
    }
}

enum ANSIStripper {
    static func strip(_ text: String) -> String {
        text.replacingOccurrences(
            of: "\u{001B}\\[[0-9;]*[A-Za-z]",
            with: "",
            options: .regularExpression
        )
    }
}

/// Thread-safe stdout line splitting for Process pipe callbacks.
private final class OutputLineBuffer: @unchecked Sendable {
    private var buffer = Data()
    private let queue = DispatchQueue(label: "io.vtools.webaudit.scan.stdout")

    func append(_ chunk: Data, onLine: @escaping (String) -> Void) {
        queue.sync {
            buffer.append(chunk)
            emitCompleteLines(onLine: onLine)
        }
    }

    func drainTail(onLine: @escaping (String) -> Void) {
        queue.sync {
            emitCompleteLines(onLine: onLine)
            guard !buffer.isEmpty, let tail = String(data: buffer, encoding: .utf8) else { return }
            let cleaned = ANSIStripper.strip(tail)
            if !cleaned.isEmpty { onLine(cleaned) }
            buffer.removeAll()
        }
    }

    private func emitCompleteLines(onLine: (String) -> Void) {
        while let range = buffer.range(of: Data([0x0a])) {
            let lineData = buffer.subdata(in: buffer.startIndex..<range.lowerBound)
            buffer.removeSubrange(buffer.startIndex...range.lowerBound)
            guard let line = String(data: lineData, encoding: .utf8) else { continue }
            let cleaned = ANSIStripper.strip(line)
            if !cleaned.isEmpty { onLine(cleaned) }
        }
    }
}

/// Ensures the scan continuation resumes at most once.
private final class ContinuationGuard: @unchecked Sendable {
    private let resumed = OSAllocatedUnfairLock(initialState: false)
    private let continuation: CheckedContinuation<URL, Error>

    init(_ continuation: CheckedContinuation<URL, Error>) {
        self.continuation = continuation
    }

    func finishOnce(_ result: Result<URL, Error>, clearProcess: @escaping () -> Void) {
        let shouldResume = resumed.withLock { done -> Bool in
            guard !done else { return false }
            done = true
            return true
        }
        guard shouldResume else { return }
        clearProcess()
        continuation.resume(with: result)
    }
}
