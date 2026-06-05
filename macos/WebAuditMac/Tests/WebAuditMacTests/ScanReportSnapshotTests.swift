import XCTest
@testable import WebAuditMac

final class ScanReportSnapshotTests: XCTestCase {
    func testLoadFromRunDirectory() throws {
        let runDir = FileManager.default.temporaryDirectory
            .appendingPathComponent("webaudit-snapshot-\(UUID().uuidString)", isDirectory: true)
        try FileManager.default.createDirectory(at: runDir, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: runDir) }

        let json = """
        {
          "meta": {
            "target_url": "https://example.com/",
            "framework": "wordpress",
            "finished_at": "2026-06-05T12:00:00Z"
          },
          "scores": {
            "hygiene": 82,
            "exposure": 100,
            "verdict": "NEEDS_ATTENTION"
          },
          "findings": [
            {
              "class": "ACTION",
              "category": "HEADERS",
              "item": "Missing CSP",
              "detail": "No Content-Security-Policy header",
              "severity": "HIGH"
            }
          ],
          "artifacts": {
            "inventory": {
              "framework": { "name": "wordpress", "confidence": "high" },
              "html": { "pages_scanned": 3 },
              "paths": { "probe_count": 42 }
            },
            "tls": { "certificate": { "days_left": 90 } }
          }
        }
        """
        try json.write(
            to: runDir.appendingPathComponent("audit_run.json"),
            atomically: true,
            encoding: .utf8
        )

        let snapshot = try XCTUnwrap(ScanReportSnapshot.load(from: runDir))
        XCTAssertEqual(snapshot.hygiene, 82)
        XCTAssertEqual(snapshot.exposure, 100)
        XCTAssertEqual(snapshot.verdict, "NEEDS_ATTENTION")
        XCTAssertEqual(snapshot.hostLabel, "example.com")
        XCTAssertEqual(snapshot.actionCount, 1)
    }
}
