// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "AIOSCaptureCore",
    platforms: [
        .iOS(.v17),
        .watchOS(.v10),
        .macOS(.v12),
    ],
    products: [
        .library(
            name: "AIOSCaptureCore",
            targets: ["AIOSCaptureCore"]
        ),
    ],
    targets: [
        .target(
            name: "AIOSCaptureCore"
        ),
        .testTarget(
            name: "AIOSCaptureCoreTests",
            dependencies: ["AIOSCaptureCore"]
        ),
    ]
)
