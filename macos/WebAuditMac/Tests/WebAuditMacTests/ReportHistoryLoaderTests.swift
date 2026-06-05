import XCTest
@testable import WebAuditMac

final class ReportHistoryLoaderTests: XCTestCase {
    func testLoadScansSkipsLogsAndFindsReports() throws {
        let root = FileManager.default.temporaryDirectory
            .appendingPathComponent("webaudit-history-\(UUID().uuidString)", isDirectory: true)
        defer { try? FileManager.default.removeItem(at: root) }
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)

        let logs = root.appendingPathComponent("Logs", isDirectory: true)
        try FileManager.default.createDirectory(at: logs, withIntermediateDirectories: true)
        try "log".write(to: logs.appendingPathComponent("scan-failure.txt"), atomically: true, encoding: .utf8)

        let run = root.appendingPathComponent("2026-06-05T12-00-00Z_example.com", isDirectory: true)
        try FileManager.default.createDirectory(at: run, withIntermediateDirectories: true)
        let json: [String: Any] = [
            "meta": ["target_url": "https://example.com", "finished_at": "2026-06-05T12:00:00Z"],
            "scores": ["verdict": "PASS", "hygiene": 90, "exposure": 88],
        ]
        let data = try JSONSerialization.data(withJSONObject: json)
        try data.write(to: run.appendingPathComponent("audit_run.json"))
        try "<html></html>".write(to: run.appendingPathComponent("report.html"), atomically: true, encoding: .utf8)

        let scans = ReportHistoryLoader.loadScans(from: root)
        XCTAssertEqual(scans.count, 1)
        XCTAssertEqual(scans[0].url, "https://example.com")
        XCTAssertEqual(scans[0].hostLabel, "example.com")
        XCTAssertEqual(scans[0].verdict, "PASS")
    }
}
