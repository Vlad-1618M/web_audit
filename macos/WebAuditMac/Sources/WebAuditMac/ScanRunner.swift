import Foundation
import Darwin
import os

/// Locates and runs webaudit-docker or native webaudit; streams combined stdout/stderr.
final class ScanRunner {
    static let outputRoot = FileManager.default.homeDirectoryForCurrentUser
        .appendingPathComponent("Documents/WebAudit", isDirectory: true)

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
            throw ScanRunnerError.engineMissing
        }
        return engine
    }

    func detectEngine() -> ScanEngineInfo {
        let candidates = resolveDockerWrapperCandidates() + resolveWebauditCandidates()
        for path in candidates {
            if isRunnable(at: path) {
                let kind: ScanEngineInfo.Kind = path.contains("webaudit-docker") ? .webauditDocker : .webauditCLI
                return ScanEngineInfo(kind: kind, path: path, detail: "Ready")
            }
        }
        return ScanEngineInfo(
            kind: .none,
            path: "",
            detail: "Install webaudit-docker (see README) or webaudit on PATH"
        )
    }

    func runScan(url: String, onLine: @escaping (String) -> Void) async throws -> URL {
        let engine = try prepareScan()

        let process = Process()
        let pipe = Pipe()
        process.standardOutput = pipe
        process.standardError = pipe
        process.environment = Self.subprocessEnvironment()

        switch engine.kind {
        case .webauditDocker:
            configureProcess(process, scriptPath: engine.path, arguments: [
                "--output-dir", "documents",
                "--open", "none",
                "-y",
                "scan", url,
                "-v",
            ])
        case .webauditCLI:
            process.executableURL = URL(fileURLWithPath: engine.path)
            process.arguments = [
                "scan", url,
                "-v",
                "--open", "none",
                "-o", Self.outputRoot.path,
            ]
        case .none:
            throw ScanRunnerError.engineMissing
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

    private func resolveDockerWrapperCandidates() -> [String] {
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
        return paths
    }

    private func resolveWebauditCandidates() -> [String] {
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
        return paths
    }

    /// GUI launches (Finder, Dock, Launchpad) get a minimal PATH. Terminal tools like
    /// `docker` and `webaudit-docker` live in Homebrew, Docker.app, or ~/.local/bin.
    private static func subprocessEnvironment() -> [String: String] {
        var env = ProcessInfo.processInfo.environment
        let home = FileManager.default.homeDirectoryForCurrentUser.path
        let extraPaths = [
            "\(home)/.local/bin",
            "/opt/homebrew/bin",
            "/opt/homebrew/sbin",
            "/usr/local/bin",
            "/Applications/Docker.app/Contents/Resources/bin",
        ]
        let existing = env["PATH"] ?? "/usr/bin:/bin:/usr/sbin:/sbin"
        var seen = Set<String>()
        var parts: [String] = []
        for segment in extraPaths + existing.split(separator: ":").map(String.init) {
            guard !segment.isEmpty, seen.insert(segment).inserted else { continue }
            parts.append(segment)
        }
        env["PATH"] = parts.joined(separator: ":")
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
        if scriptPath.hasSuffix(".sh") {
            process.executableURL = URL(fileURLWithPath: "/bin/bash")
            process.arguments = [scriptPath] + arguments
        } else {
            process.executableURL = URL(fileURLWithPath: scriptPath)
            process.arguments = arguments
        }
    }
}

enum ScanRunnerError: LocalizedError {
    case engineMissing
    case scanFailed(code: Int)
    case reportNotFound

    var errorDescription: String? {
        switch self {
        case .engineMissing:
            return """
            Scan engine not found. Install once:
            • Docker: webaudit-docker → ~/.local/bin (see v2_python_core/docs/docker_ci.md)
            • Or: pip install webaudit / dev venv with webaudit on PATH
            """
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
