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
}

class TestBaseClass {
	func someFunc() {
		let y = TestStructA(testStructAInt: 1, testStructAString: 2)
	}
}

class TestClass: TestBaseClass {
	override func someFunc() {
		super.someFunc()
	}
}