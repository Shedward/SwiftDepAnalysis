struct TestStructA {
	let testStructAInt: Int 
	let testStructAString: String
}

struct TestStructB {
	let testStructBStructA: TestStructA
}

enum TestEnum {
	case some
	case another(TestStructB)

	func enumFunc() {
		let x = TestStructA(testStructAInt: 1, testStructAString: 2)
	}

	static func from(other: TestEnum) -> TestEnum {

	}
}

class TestBaseClass {
	func someFunc() {
		let y = TestStructA(testStructAInt: 1, testStructAString: 2)
	}

	func someFunc(b: TestStructB) {
		struct SomeResult {
			let someValue: x
		}
		if b.testStructBStructA.testStructAInt > 2 {
			for i in 0...5 {
				print(i)
				switch i {
					case 0:
						print(0)
					case 1:
						print(2)
						enum SwitchEnum {
							protocol HiddenProtocol {
								var value: Int { get set }
							}
							protocol ChildHiddenProtocol: HiddenProtocol {
								var childValue: SomeResult { get set }
							}
						}
					case 2:
						print("Some")
					default:
						print("Wrong")
				}
			}
		}
	}
}

class TestClass: TestBaseClass {
	override func someFunc() {
		super.someFunc()
	}
}