select * from balance_general;

CREATE VIEW balance_general AS
SELECT 
  c.id AS cuenta_id,
  c.numero_cuenta,
  c.fecha_registro,
  DATE_FORMAT(g.fecha, '%Y-%m') AS mes,
  SUM(CASE 
    WHEN g.fecha < DATE_FORMAT(g.fecha, '%Y-%m-01') THEN g.monto 
    ELSE 0 
  END) AS saldo_anterior,
  SUM(CASE 
    WHEN g.fecha >= DATE_FORMAT(g.fecha, '%Y-%m-01') THEN g.monto 
    ELSE 0 
  END) AS saldo_inicial,
  SUM(g.monto) AS balance_general
FROM 
  gastos_cuenta c
LEFT JOIN 
  gastos_gastos g ON c.id = g.id_cuenta_banco_id
LEFT JOIN 
  ventas_ventas v ON c.id = v.sucursal_id_id
LEFT JOIN 
  gastos_compra p ON c.id = p.productor_id
GROUP BY 
  c.id, c.numero_cuenta, c.fecha_registro, DATE_FORMAT(g.fecha, '%Y-%m');