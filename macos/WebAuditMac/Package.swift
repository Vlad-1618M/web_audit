// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "WebAuditMac",
    platforms: [.macOS(.v13)],
    products: [
        .executable(name: "WebAuditMac", targets: ["WebAuditMac"]),
    ],
    targets: [
        .executableTarget(
            name: "WebAuditMac",
            path: "Sources/WebAuditMac",
            resources: [.process("Resources")]
        ),
    ]
)
