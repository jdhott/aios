import XCTest
@testable import AIOSCaptureCore

final class BrainDumpFormatterTests: XCTestCase {
    func testSplitStripsBulletMarkers() {
        let lines = BrainDumpFormatter.split("• Buy milk\n- Call dentist")
        XCTAssertEqual(lines, ["Buy milk", "Call dentist"])
    }

    func testSplitIgnoresBlankLines() {
        let lines = BrainDumpFormatter.split("• One\n\n• Two")
        XCTAssertEqual(lines, ["One", "Two"])
    }

    func testNormalizedDraftCapitalizesBullets() {
        let value = BrainDumpFormatter.normalizedDraft("buy milk")
        XCTAssertEqual(value, "• Buy milk")
    }
}
