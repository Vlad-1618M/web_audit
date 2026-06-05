import XCTest
@testable import WebAuditMac

final class ScanFailureLogTests: XCTestCase {
    func testWriteIncludesURLDateAndOutput() throws {
        let temp = FileManager.default.temporaryDirectory
            .appendingPathComponent("webaudit-log-test-\(UUID().uuidString)", isDirectory: true)
        defer { try? FileManager.default.removeItem(at: temp) }

        let started = Date(timeIntervalSince1970: 1_700_000_000)
        let failed = started.addingTimeInterval(42)
        let context = ScanFailureLogWriter.Context(
            scannedURL: "https://example.com/path",
            errorMessage: "Scan failed (exit 1). See log above.",
            logLines: ["line one", "Traceback (most recent call last):"],
            engine: ScanEngineInfo(kind: .bundled, path: "/tmp/webaudit", detail: "Ready"),
            startedAt: started,
            failedAt: failed
        )

        let fileURL = try ScanFailureLogWriter.write(context, logsDirectory: temp)
        XCTAssertTrue(FileManager.default.fileExists(atPath: fileURL.path))

        let text = try String(contentsOf: fileURL, encoding: .utf8)
        XCTAssertTrue(text.contains("https://example.com/path"))
        XCTAssertTrue(text.contains("Scan failed (exit 1)"))
        XCTAssertTrue(text.contains("line one"))
        XCTAssertTrue(text.contains("Traceback"))
        XCTAssertTrue(text.contains("Engine kind:"))
        XCTAssertTrue(text.contains("bundled webaudit"))
        XCTAssertTrue(fileURL.lastPathComponent.contains("example.com"))
    }
}
