import XCTest
@testable import WebAuditMac

final class ScanRunnerTests: XCTestCase {
    func testBundledScanArgumentsIncludeJs() {
        let args = ScanRunner.scanProcessArguments(
            engineKind: .bundled,
            url: "https://example.com"
        )
        XCTAssertEqual(args, [
            "scan", "https://example.com",
            "-v",
            "--js",
            "--open", "none",
            "-o", ScanRunner.outputRoot.path,
        ])
    }

    func testHostCliScanArgumentsIncludeJs() {
        let args = ScanRunner.scanProcessArguments(
            engineKind: .webauditCLI,
            url: "https://example.com"
        )
        XCTAssertTrue(args.contains("--js"))
        XCTAssertEqual(args.first, "scan")
    }

    func testDockerScanArgumentsIncludeJs() {
        let args = ScanRunner.scanProcessArguments(
            engineKind: .webauditDocker,
            url: "https://example.com"
        )
        XCTAssertEqual(args, [
            "--output-dir", "documents",
            "--open", "none",
            "-y",
            "scan", "https://example.com",
            "-v",
            "--js",
        ])
    }
}
