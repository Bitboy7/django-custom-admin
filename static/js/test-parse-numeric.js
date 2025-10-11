/**
 * Script de prueba para parseNumericString
 * Ejecutar en la consola del navegador después de cargar datatables-utils.js
 */

console.log("=== Testing parseNumericString ===\n");

const testCases = [
  {
    input: "$32 234.00",
    expected: 32234.0,
    description: "Formato con espacios y símbolo",
  },
  {
    input: "$32,234.00",
    expected: 32234.0,
    description: "Formato americano estándar",
  },
  {
    input: "32 234",
    expected: 32234,
    description: "Solo espacios sin decimales",
  },
  {
    input: "32 234.50",
    expected: 32234.5,
    description: "Espacios con decimales",
  },
  {
    input: "1 234 567.89",
    expected: 1234567.89,
    description: "Número grande con espacios",
  },
  {
    input: "$1,234.56",
    expected: 1234.56,
    description: "Formato americano con $",
  },
  { input: "€1.234,56", expected: 1234.56, description: "Formato europeo" },
  { input: "1.234,56", expected: 1234.56, description: "Europeo sin símbolo" },
  {
    input: "32\u00A0234.00",
    expected: 32234.0,
    description: "Con nbsp (\\u00A0)",
  },
  {
    input: "32&nbsp;234.00",
    expected: 32234.0,
    description: "Con entidad HTML nbsp",
  },
];

let allPassed = true;
let passCount = 0;
let failCount = 0;

testCases.forEach((test, index) => {
  const result = parseNumericString(test.input);
  const passed = Math.abs(result - test.expected) < 0.01;

  if (passed) {
    passCount++;
    console.log(`✅ Test ${index + 1}: ${test.description}`);
    console.log(`   Input: "${test.input}" → Output: ${result}`);
  } else {
    failCount++;
    allPassed = false;
    console.error(`❌ Test ${index + 1}: ${test.description}`);
    console.error(`   Input: "${test.input}"`);
    console.error(`   Expected: ${test.expected}, Got: ${result}`);
  }
});

console.log("\n=== Resumen ===");
console.log(`Total: ${testCases.length} tests`);
console.log(`✅ Pasados: ${passCount}`);
console.log(`❌ Fallidos: ${failCount}`);

if (allPassed) {
  console.log("\n🎉 ¡Todos los tests pasaron!");
} else {
  console.log("\n⚠️ Algunos tests fallaron. Revisa los detalles arriba.");
}
