import XCTest
@testable import WebAuditMac

final class ReportBundleExporterTests: XCTestCase {
    func testZipContainsHtmlCssAndReadme() throws {
        let runDir = FileManager.default.temporaryDirectory
            .appendingPathComponent("webaudit-test-\(UUID().uuidString)", isDirectory: true)
        try FileManager.default.createDirectory(at: runDir, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: runDir) }

        try "<html><link rel=\"stylesheet\" href=\"report.css\"></html>"
            .write(to: runDir.appendingPathComponent("report.html"), atomically: true, encoding: .utf8)
        try "body { color: red; }"
            .write(to: runDir.appendingPathComponent("report.css"), atomically: true, encoding: .utf8)

        let zipURL = try ReportBundleExporter.createShareableZip(from: runDir, hostLabel: "example.com")
        defer { try? FileManager.default.removeItem(at: zipURL) }

        XCTAssertTrue(FileManager.default.fileExists(atPath: zipURL.path))
        XCTAssertTrue(zipURL.pathExtension == "zip")
        XCTAssertTrue(ReportBundleExporter.defaultZipName(hostLabel: "example.com").contains("example.com"))
    }
}
