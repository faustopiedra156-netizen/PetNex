$ErrorActionPreference = 'Stop'

$docsDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$out = Join-Path $docsDir 'Resumen_Modelo_Negocio_Digital_PetNexo.docx'
$tmp = Join-Path $env:TEMP ('petnexo_modelo_' + [guid]::NewGuid().ToString())

New-Item -ItemType Directory -Path $tmp | Out-Null
New-Item -ItemType Directory -Path (Join-Path $tmp '_rels') | Out-Null
New-Item -ItemType Directory -Path (Join-Path $tmp 'word') | Out-Null
New-Item -ItemType Directory -Path (Join-Path $tmp 'word\_rels') | Out-Null

function Escape-Xml([string]$Text) {
    return [System.Security.SecurityElement]::Escape($Text)
}

function Add-Paragraph([string]$Text, [string]$Style = 'Normal') {
    $styleXml = ''
    if ($Style -ne 'Normal') {
        $styleXml = '<w:pPr><w:pStyle w:val="' + $Style + '"/></w:pPr>'
    }
    return '<w:p>' + $styleXml + '<w:r><w:t xml:space="preserve">' + (Escape-Xml $Text) + '</w:t></w:r></w:p>'
}

function Add-Bullet([string]$Text) {
    return '<w:p><w:pPr><w:pStyle w:val="ListParagraph"/><w:numPr><w:ilvl w:val="0"/><w:numId w:val="1"/></w:numPr></w:pPr><w:r><w:t xml:space="preserve">' + (Escape-Xml $Text) + '</w:t></w:r></w:p>'
}

function Add-PageBreak() {
    return '<w:p><w:r><w:br w:type="page"/></w:r></w:p>'
}

$body = New-Object System.Collections.Generic.List[string]

$body.Add((Add-Paragraph 'Desarrollo y validacion del modelo de negocio digital' 'Title'))
$body.Add((Add-Paragraph 'Proyecto: PetNexo, plataforma web para gestion de locales de peluqueria, estetica y cuidado de mascotas.' 'Subtitle'))
$body.Add((Add-Paragraph ('Fecha de generacion: ' + (Get-Date -Format 'yyyy-MM-dd HH:mm'))))

$body.Add((Add-Paragraph 'Resumen ejecutivo' 'Heading1'))
$body.Add((Add-Paragraph 'PetNexo es una solucion digital tipo SaaS orientada a negocios que ofrecen servicios de peluqueria, estetica, bano, spa, higiene y cuidado de mascotas. El sistema permite que cada local administre su catalogo, sucursales, horarios, citas, clientes, mascotas, pagos, seguimiento del servicio y resenas desde una plataforma centralizada.'))
$body.Add((Add-Paragraph 'La oportunidad nace de un problema frecuente en este tipo de negocios: gran parte de las reservas se coordina por WhatsApp o llamadas, los horarios se manejan manualmente, el cliente no tiene visibilidad del avance de su mascota y el dueno del local carece de informacion clara sobre ventas, demanda y satisfaccion. PetNexo busca reducir esa friccion y profesionalizar la operacion diaria.'))

$body.Add((Add-Paragraph 'Problema identificado' 'Heading1'))
@(
    'Los locales pierden tiempo coordinando citas por mensajes, llamadas o agendas fisicas.',
    'Es comun que existan cruces de horarios, olvidos, cancelaciones tardias o espacios vacios.',
    'Los clientes desean saber que servicio recibe su mascota, en que estado va y cuando puede retirarla.',
    'Muchos negocios pequenos no tienen una herramienta simple para publicar servicios, cobrar, recibir resenas y medir resultados.',
    'Cuando el local tiene mas de una sucursal, la gestion de disponibilidad se vuelve mas dificil si no se separan horarios por local.'
) | ForEach-Object { $body.Add((Add-Bullet $_)) }

$body.Add((Add-Paragraph 'Solucion propuesta' 'Heading1'))
$body.Add((Add-Paragraph 'PetNexo centraliza la operacion de un negocio de cuidado de mascotas en una plataforma web construida con Django. El cliente final puede registrarse, crear la ficha de su mascota, reservar una cita, pagar o seleccionar metodo de pago, revisar el seguimiento y dejar una calificacion. El administrador del local puede gestionar servicios, precios, horarios, sucursales, citas y estados de atencion. El dueno de PetNexo controla el sistema, los planes y las cuentas de locales.'))

$body.Add((Add-Paragraph 'Propuesta de valor' 'Heading1'))
@(
    'Para el local: menos trabajo manual, mejor control de agenda, organizacion por sucursales, catalogo editable, pagos y datos para tomar decisiones.',
    'Para el cliente final: reserva mas rapida, seguimiento de la mascota, informacion clara de precios, horarios y servicios.',
    'Para PetNexo: modelo escalable por suscripcion mensual o anual, adaptable a distintos negocios del sector mascotas.',
    'Diferenciador principal: combina reservas, operacion interna, seguimiento y monetizacion SaaS en una sola herramienta.'
) | ForEach-Object { $body.Add((Add-Bullet $_)) }

$body.Add((Add-Paragraph 'Modelo Canvas del negocio digital' 'Heading1'))
$body.Add((Add-Paragraph 'Segmentos de clientes' 'Heading2'))
@(
    'Locales de peluqueria canina, estetica de mascotas, veterinarias con servicios de grooming y spas para mascotas.',
    'Emprendimientos pequenos que necesitan digitalizar reservas sin comprar un sistema complejo.',
    'Negocios con una o varias sucursales que requieren separar horarios y disponibilidad.',
    'Clientes finales que buscan reservar, pagar y consultar el estado de atencion de su mascota.'
) | ForEach-Object { $body.Add((Add-Bullet $_)) }

$body.Add((Add-Paragraph 'Canales' 'Heading2'))
@(
    'Pagina web publica de cada local configurada con su nombre, ciudad, contacto, servicios y marca.',
    'Redes sociales del negocio, enlaces en Instagram, Facebook, TikTok y WhatsApp.',
    'Ventas directas a locales de mascotas en la ciudad.',
    'Demostraciones del sistema y pruebas piloto con negocios reales.'
) | ForEach-Object { $body.Add((Add-Bullet $_)) }

$body.Add((Add-Paragraph 'Relacion con clientes' 'Heading2'))
@(
    'Autoservicio para reservas, registro de mascotas y consulta de citas.',
    'Acompanamiento inicial al administrador del local para configurar servicios, horarios y sucursales.',
    'Soporte por correo o WhatsApp para incidencias operativas.',
    'Renovacion por suscripcion mensual o anual.'
) | ForEach-Object { $body.Add((Add-Bullet $_)) }

$body.Add((Add-Paragraph 'Fuentes de ingresos' 'Heading2'))
@(
    'Plan Basico: $25 mensuales para un local pequeno con funciones esenciales.',
    'Plan Pro: $45 mensuales para negocios en crecimiento con mayor capacidad.',
    'Plan Premium: $75 mensuales para negocios con mas sucursales y mayor volumen.',
    'Plan anual con descuento para mejorar retencion y flujo de caja.',
    'Servicios adicionales: configuracion inicial, personalizacion, soporte premium o modulos avanzados.'
) | ForEach-Object { $body.Add((Add-Bullet $_)) }

$body.Add((Add-Paragraph 'Recursos clave' 'Heading2'))
@(
    'Plataforma Django, base de datos PostgreSQL/Supabase y despliegue en Vercel para pruebas.',
    'Sistema de autenticacion, roles, panel de gestion y flujo de reservas.',
    'Integracion preparada para pagos con tarjeta, transferencia y pago fisico.',
    'Marca PetNexo, documentacion de entrega y material comercial para demostraciones.'
) | ForEach-Object { $body.Add((Add-Bullet $_)) }

$body.Add((Add-Paragraph 'Actividades clave' 'Heading2'))
@(
    'Desarrollo, mantenimiento y mejora continua de la plataforma.',
    'Onboarding de locales: carga de servicios, horarios, sucursales y datos del negocio.',
    'Pruebas de calidad antes de activar cada local.',
    'Soporte, monitoreo de errores y analisis de metricas de uso.'
) | ForEach-Object { $body.Add((Add-Bullet $_)) }

$body.Add((Add-Paragraph 'Socios clave' 'Heading2'))
@(
    'Supabase como proveedor de base de datos PostgreSQL.',
    'Vercel como plataforma de despliegue para pruebas y demostracion.',
    'Google Cloud para autenticacion con cuentas de Google.',
    'Datafast u otra pasarela local para cobros con tarjeta.',
    'Locales piloto que permitan validar el producto en condiciones reales.'
) | ForEach-Object { $body.Add((Add-Bullet $_)) }

$body.Add((Add-Paragraph 'Estructura de costos' 'Heading2'))
@(
    'Hosting, base de datos, dominio, correos y herramientas de monitoreo.',
    'Comisiones de pasarela de pago.',
    'Tiempo de desarrollo, soporte y mantenimiento.',
    'Marketing, ventas, demostraciones y capacitacion.',
    'Costos legales, politicas de privacidad, terminos de uso y proteccion de datos.'
) | ForEach-Object { $body.Add((Add-Bullet $_)) }

$body.Add((Add-PageBreak))
$body.Add((Add-Paragraph 'Validacion del modelo de negocio' 'Heading1'))
$body.Add((Add-Paragraph 'Para validar PetNexo se recomienda trabajar con un MVP funcional en uno o dos locales reales. La validacion debe medir si el sistema resuelve el problema de agenda, mejora la experiencia del cliente y si el dueno del local estaria dispuesto a pagar una suscripcion.'))

$body.Add((Add-Paragraph 'Hipotesis principales' 'Heading2'))
@(
    'Los locales estan dispuestos a pagar desde $25 mensuales si el sistema reduce tiempo operativo y mejora reservas.',
    'Los clientes finales prefieren reservar desde una pagina web si el proceso es rapido y claro.',
    'El seguimiento de mascota aumenta confianza y mejora la percepcion del servicio.',
    'Las resenas y calificaciones ayudan al local a mejorar reputacion y conversion.',
    'La gestion por sucursales es necesaria para locales con mas de un punto de atencion.'
) | ForEach-Object { $body.Add((Add-Bullet $_)) }

$body.Add((Add-Paragraph 'Metricas para validar' 'Heading2'))
@(
    'Numero de citas agendadas por semana desde la plataforma.',
    'Porcentaje de citas completadas frente a canceladas.',
    'Tiempo promedio que el administrador tarda en registrar o confirmar una cita.',
    'Cantidad de clientes registrados y mascotas creadas.',
    'Calificacion promedio por servicio y comentarios recibidos.',
    'Ingresos generados por suscripciones y tasa de renovacion.',
    'Uso de metodos de pago: tarjeta, transferencia y pago fisico.'
) | ForEach-Object { $body.Add((Add-Bullet $_)) }

$body.Add((Add-Paragraph 'Experimentos de validacion' 'Heading2'))
@(
    'Piloto con un local durante 30 dias usando plan gratuito o demo controlada.',
    'Comparar reservas manuales frente a reservas digitales antes y despues del piloto.',
    'Entrevistar al dueno del local sobre facilidad de uso, valor percibido y disposicion de pago.',
    'Pedir a clientes finales que agenden una cita y califiquen la experiencia.',
    'Probar dos precios de suscripcion para conocer sensibilidad al precio.',
    'Medir si los recordatorios, seguimiento y resenas aumentan recompra.'
) | ForEach-Object { $body.Add((Add-Bullet $_)) }

$body.Add((Add-Paragraph 'Estado del producto' 'Heading1'))
@(
    'Pagina publica parametrizable por negocio.',
    'Catalogo de servicios editable por administrador del local.',
    'Registro, login tradicional y preparacion para autenticacion con Google.',
    'Agenda con fecha, hora, mascota, servicio y sucursal.',
    'Panel de administracion para citas, servicios, sucursales y configuracion.',
    'Seguimiento de mascota y calificaciones con estrellas.',
    'Planes de suscripcion y flujo de pago preparado.',
    'Chatbot de asistencia basica.',
    'Preparacion para despliegue en Vercel con variables de entorno.'
) | ForEach-Object { $body.Add((Add-Bullet $_)) }

$body.Add((Add-Paragraph 'Riesgos y pendientes antes de salir al publico' 'Heading1'))
@(
    'Probar todas las migraciones en Supabase real y no solo en SQLite local.',
    'Configurar credenciales reales de Google OAuth y validar el callback en produccion.',
    'Configurar pasarela de pagos real para que el dinero llegue a la cuenta del dueno de PetNexo.',
    'Activar DEBUG=False, SECRET_KEY segura, ALLOWED_HOSTS y CSRF_TRUSTED_ORIGINS con dominio final.',
    'Crear politica de privacidad, terminos de uso y proceso de soporte.',
    'Definir respaldo de base de datos y monitoreo de errores.',
    'Realizar pruebas con roles: dueno PetNexo, administrador del local y cliente final.',
    'Validar diseno responsive en celular, tablet y escritorio.'
) | ForEach-Object { $body.Add((Add-Bullet $_)) }

$body.Add((Add-Paragraph 'Conclusion' 'Heading1'))
$body.Add((Add-Paragraph 'PetNexo tiene una propuesta de negocio digital viable porque ataca una necesidad real de locales de cuidado de mascotas: ordenar reservas, mejorar comunicacion con clientes, mostrar servicios, gestionar pagos y profesionalizar la atencion. El modelo por suscripcion permite ingresos recurrentes y puede escalar a distintos locales si se completa la validacion tecnica, comercial y operativa. Para llevarlo al mercado se recomienda ejecutar un piloto controlado, medir resultados durante 30 dias y ajustar precios, funciones y soporte segun la respuesta de los primeros usuarios.'))

$bodyXml = $body -join "`n"
$documentXml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>' + $bodyXml + '<w:sectPr><w:pgSz w:w="12240" w:h="15840"/><w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" w:header="708" w:footer="708" w:gutter="0"/></w:sectPr></w:body></w:document>'

$contentTypes = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/><Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/><Override PartName="/word/numbering.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.numbering+xml"/></Types>'
$rels = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>'
$docRels = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/numbering" Target="numbering.xml"/></Relationships>'
$styles = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:qFormat/><w:pPr><w:spacing w:after="120" w:line="280" w:lineRule="auto"/></w:pPr><w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/><w:sz w:val="22"/><w:color w:val="1F2937"/></w:rPr></w:style><w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:basedOn w:val="Normal"/><w:qFormat/><w:pPr><w:spacing w:after="220"/></w:pPr><w:rPr><w:b/><w:color w:val="00685F"/><w:sz w:val="40"/></w:rPr></w:style><w:style w:type="paragraph" w:styleId="Subtitle"><w:name w:val="Subtitle"/><w:basedOn w:val="Normal"/><w:qFormat/><w:pPr><w:spacing w:after="180"/></w:pPr><w:rPr><w:color w:val="475569"/><w:sz w:val="24"/></w:rPr></w:style><w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/><w:pPr><w:spacing w:before="320" w:after="140"/><w:outlineLvl w:val="0"/></w:pPr><w:rPr><w:b/><w:color w:val="0F172A"/><w:sz w:val="30"/></w:rPr></w:style><w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/><w:pPr><w:spacing w:before="220" w:after="100"/><w:outlineLvl w:val="1"/></w:pPr><w:rPr><w:b/><w:color w:val="00685F"/><w:sz w:val="25"/></w:rPr></w:style><w:style w:type="paragraph" w:styleId="ListParagraph"><w:name w:val="List Paragraph"/><w:basedOn w:val="Normal"/><w:pPr><w:ind w:left="720"/></w:pPr></w:style></w:styles>'
$numbering = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:numbering xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:abstractNum w:abstractNumId="0"><w:multiLevelType w:val="hybridMultilevel"/><w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="bullet"/><w:lvlText w:val="-"/><w:lvlJc w:val="left"/><w:pPr><w:ind w:left="720" w:hanging="360"/></w:pPr></w:lvl></w:abstractNum><w:num w:numId="1"><w:abstractNumId w:val="0"/></w:num></w:numbering>'

[System.IO.File]::WriteAllText((Join-Path $tmp '[Content_Types].xml'), $contentTypes, [System.Text.Encoding]::UTF8)
[System.IO.File]::WriteAllText((Join-Path $tmp '_rels\.rels'), $rels, [System.Text.Encoding]::UTF8)
[System.IO.File]::WriteAllText((Join-Path $tmp 'word\_rels\document.xml.rels'), $docRels, [System.Text.Encoding]::UTF8)
[System.IO.File]::WriteAllText((Join-Path $tmp 'word\document.xml'), $documentXml, [System.Text.Encoding]::UTF8)
[System.IO.File]::WriteAllText((Join-Path $tmp 'word\styles.xml'), $styles, [System.Text.Encoding]::UTF8)
[System.IO.File]::WriteAllText((Join-Path $tmp 'word\numbering.xml'), $numbering, [System.Text.Encoding]::UTF8)

if (Test-Path $out) {
    Remove-Item $out -Force
}

Add-Type -AssemblyName System.IO.Compression.FileSystem
[System.IO.Compression.ZipFile]::CreateFromDirectory($tmp, $out)
Remove-Item $tmp -Recurse -Force

Get-Item $out
