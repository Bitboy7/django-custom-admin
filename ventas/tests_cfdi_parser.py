"""
Pruebas unitarias del parser CFDI 3.3 / 4.0 y de la clasificación de subtipos.

Ejecución:
    python manage.py test ventas.tests_cfdi_parser --verbosity=2
"""
from django.test import SimpleTestCase

from ventas.cfdi_parser import parse_cfdi, classify_subtipo


XML_40_INGRESO = """<?xml version="1.0" encoding="UTF-8"?>
<cfdi:Comprobante xmlns:cfdi="http://www.sat.gob.mx/cfd/4"
    xmlns:tfd="http://www.sat.gob.mx/TimbreFiscalDigital"
    Serie="B" Folio="1996" Fecha="2026-04-03T10:00:00" TipoDeComprobante="I"
    Moneda="MXN" Total="13125.00" MetodoPago="PUE" Exportacion="01" TipoCambio="1">
  <cfdi:Receptor Rfc="XEXX010101000" Nombre="Panorama Produce SA" UsoCFDI="G01"
      DomicilioFiscalReceptor="40906" ResidenciaFiscal="CAN"
      NumRegIdTrib="834911224" RegimenFiscalReceptor="616"/>
  <cfdi:Conceptos>
    <cfdi:Concepto ClaveProdServ="01010101" NoIdentificacion="MANILA" Cantidad="1250"
      ClaveUnidad="KGM" Descripcion="Mango Manila Tapachula" ValorUnitario="10.5" Importe="13125.00"/>
  </cfdi:Conceptos>
  <cfdi:Complemento>
    <tfd:TimbreFiscalDigital UUID="11111111-1111-1111-1111-111111111111" FechaTimbrado="2026-04-03T10:01:00"/>
  </cfdi:Complemento>
</cfdi:Comprobante>
"""

XML_33_EXPORTACION = """<?xml version="1.0" encoding="UTF-8"?>
<cfdi:Comprobante xmlns:cfdi="http://www.sat.gob.mx/cfd/3"
    xmlns:tfd="http://www.sat.gob.mx/TimbreFiscalDigital"
    xmlns:cce11="http://www.sat.gob.mx/ComercioExterior11"
    Serie="B" Folio="2001" Fecha="2026-04-13T10:00:00" TipoDeComprobante="I"
    Moneda="USD" Total="9450.00" MetodoPago="PPD" TipoCambio="17.5000">
  <cfdi:Receptor Rfc="X" Nombre="GM Produce"/>
  <cfdi:Conceptos>
    <cfdi:Concepto ClaveProdServ="01010101" Cantidad="1050" Descripcion="Mango Tommy"/>
  </cfdi:Conceptos>
  <cfdi:Complemento>
    <cce11:ComercioExterior Incoterm="FOB" TipoCambioUSD="17.5000">
      <cce11:Mercancias>
        <cce11:Mercancia FraccionArancelaria="08045002" CantidadAduana="1050"/>
      </cce11:Mercancias>
    </cce11:ComercioExterior>
    <tfd:TimbreFiscalDigital UUID="22222222-2222-2222-2222-222222222222" FechaTimbrado="2026-04-13T10:01:00"/>
  </cfdi:Complemento>
</cfdi:Comprobante>
"""

XML_EGRESO_NOTA_CREDITO = """<?xml version="1.0" encoding="UTF-8"?>
<cfdi:Comprobante xmlns:cfdi="http://www.sat.gob.mx/cfd/3"
    xmlns:tfd="http://www.sat.gob.mx/TimbreFiscalDigital"
    Serie="NC" Folio="001" Fecha="2026-05-02T10:00:00" TipoDeComprobante="E"
    Moneda="MXN" Total="520.00" MetodoPago="PUE">
  <cfdi:CfdiRelacionados TipoRelacion="01">
    <cfdi:CfdiRelacionado UUID="11111111-1111-1111-1111-111111111111"/>
  </cfdi:CfdiRelacionados>
  <cfdi:Receptor Rfc="XAXX010101000" Nombre="Panorama Produce SA"/>
  <cfdi:Conceptos>
    <cfdi:Concepto ClaveProdServ="01010101" Cantidad="1" Descripcion="Descuento por fruta en mal estado"/>
  </cfdi:Conceptos>
  <cfdi:Complemento>
    <tfd:TimbreFiscalDigital UUID="33333333-3333-3333-3333-333333333333" FechaTimbrado="2026-05-02T10:01:00"/>
  </cfdi:Complemento>
</cfdi:Comprobante>
"""

XML_NOTA_CARGO = """<?xml version="1.0" encoding="UTF-8"?>
<cfdi:Comprobante xmlns:cfdi="http://www.sat.gob.mx/cfd/4"
    xmlns:tfd="http://www.sat.gob.mx/TimbreFiscalDigital"
    Serie="NCG" Folio="002" Fecha="2026-05-03T10:00:00" TipoDeComprobante="I"
    Moneda="USD" Total="250.00" MetodoPago="PUE" Exportacion="01">
  <cfdi:CfdiRelacionados TipoRelacion="02">
    <cfdi:CfdiRelacionado UUID="11111111-1111-1111-1111-111111111111"/>
  </cfdi:CfdiRelacionados>
  <cfdi:Receptor Rfc="X" Nombre="GM Produce"/>
  <cfdi:Conceptos>
    <cfdi:Concepto ClaveProdServ="01010101" Cantidad="1" Descripcion="Cobro de flete"/>
  </cfdi:Conceptos>
  <cfdi:Complemento>
    <tfd:TimbreFiscalDigital UUID="44444444-4444-4444-4444-444444444444" FechaTimbrado="2026-05-03T10:01:00"/>
  </cfdi:Complemento>
</cfdi:Comprobante>
"""

XML_RECIBO_PAGO = """<?xml version="1.0" encoding="UTF-8"?>
<cfdi:Comprobante xmlns:cfdi="http://www.sat.gob.mx/cfd/4"
    xmlns:tfd="http://www.sat.gob.mx/TimbreFiscalDigital"
    xmlns:pago10="http://www.sat.gob.mx/Pagos"
    Serie="REP" Folio="100" Fecha="2026-05-05T10:00:00" TipoDeComprobante="P"
    Moneda="XXX" Total="0" MetodoPago="PUE" Exportacion="01">
  <cfdi:Receptor Rfc="XAXX010101000" Nombre="Panorama Produce SA"/>
  <cfdi:Conceptos>
    <cfdi:Concepto ClaveProdServ="84111506" Cantidad="1" Descripcion="Pago"/>
  </cfdi:Conceptos>
  <cfdi:Complemento>
    <pago10:Pagos>
      <pago10:Pago FechaPago="2026-05-05T00:00:00" FormaDePagoP="03" MonedaP="MXN"
          Monto="5000.00" NumOperacion="12345">
        <pago10:DoctoRelacionado IdDocumento="11111111-1111-1111-1111-111111111111"
          MonedaDR="MXN" NumParcialidad="1" ImpSaldoAnt="5000.00" ImpPagado="5000.00" ImpSaldoInsoluto="0.00"/>
      </pago10:Pago>
    </pago10:Pagos>
    <tfd:TimbreFiscalDigital UUID="55555555-5555-5555-5555-555555555555" FechaTimbrado="2026-05-05T10:01:00"/>
  </cfdi:Complemento>
</cfdi:Comprobante>
"""


class CFDIParserTest(SimpleTestCase):

    def test_ingreso_40_nacional(self):
        parsed = parse_cfdi(XML_40_INGRESO.encode())
        self.assertEqual(parsed['version'], '4.0')
        self.assertEqual(parsed['tipo_comprobante'], 'I')
        self.assertEqual(parsed['folio_num'], '1996')
        self.assertEqual(parsed['uuid'], '11111111-1111-1111-1111-111111111111')
        self.assertEqual(parsed['_receptor_nombre'], 'Panorama Produce SA')
        self.assertEqual(parsed['_receptor_rfc'], 'XEXX010101000')
        self.assertEqual(parsed['_receptor_residencia_fiscal'], 'CAN')
        self.assertEqual(parsed['_receptor_num_reg_id_trib'], '834911224')
        self.assertEqual(parsed['_receptor_domicilio_fiscal'], '40906')
        self.assertEqual(parsed['_receptor_regimen_fiscal'], '616')
        self.assertEqual(classify_subtipo(parsed), 'venta_nacional')

    def test_33_exportacion_con_cce11(self):
        parsed = parse_cfdi(XML_33_EXPORTACION.encode())
        self.assertEqual(parsed['version'], '3.3')
        self.assertEqual(parsed['tipo_venta'], 'Exportación')
        self.assertEqual(parsed['incoterm'], 'FOB')
        self.assertEqual(parsed['modalidad_pago'], 'Credito')
        self.assertEqual(classify_subtipo(parsed), 'venta_exportacion')

    def test_egreso_clasifica_nota_credito(self):
        parsed = parse_cfdi(XML_EGRESO_NOTA_CREDITO.encode())
        self.assertEqual(parsed['tipo_comprobante'], 'E')
        self.assertEqual(parsed['tipo_relacion'], '01')
        self.assertEqual(classify_subtipo(parsed), 'nota_credito')

    def test_nota_cargo_tipo_relacion_02(self):
        parsed = parse_cfdi(XML_NOTA_CARGO.encode())
        self.assertEqual(parsed['tipo_relacion'], '02')
        self.assertEqual(parsed['relacionados'], ['11111111-1111-1111-1111-111111111111'])
        self.assertEqual(classify_subtipo(parsed), 'nota_cargo')

    def test_recibo_pago(self):
        parsed = parse_cfdi(XML_RECIBO_PAGO.encode())
        self.assertEqual(parsed['tipo_comprobante'], 'P')
        self.assertEqual(classify_subtipo(parsed), 'recibo_pago')
        self.assertEqual(len(parsed['pagos']), 1)
        self.assertEqual(str(parsed['pagos'][0]['monto']), '5000.00')
        self.assertEqual(parsed['pagos'][0]['doctos'][0]['uuid'],
                         '11111111-1111-1111-1111-111111111111')

    def test_remantente_por_concepto(self):
        parsed = parse_cfdi(XML_40_INGRESO.encode())
        parsed['descripcion'] = 'REMANENTE DE ANTICIPO'
        parsed['tipo_comprobante'] = 'I'
        parsed['tipo_relacion'] = ''
        self.assertEqual(classify_subtipo(parsed), 'remanente_anticipo')

    def test_xml_invalido_lanza_valueerror(self):
        with self.assertRaises(ValueError):
            parse_cfdi(b'<esto no es xml')
