from num2words import num2words
try:
    print(f"Test 7: '{num2words(7)}'")
    print(f"Test 6: '{num2words(6)}'")
    print(f"Test 7.0: '{num2words(7.0)}'")
    print(f"Test '7': '{num2words('7')}'")
    print("Library working correctly.")
except Exception as e:
    print(f"Library FAILED: {e}")
