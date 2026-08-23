$ErrorActionPreference = 'Stop'

$docsDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$out = Join-Path $docsDir 'Informe_entrega_PetNexo.docx'
$tmp = Join-Path $env:TEMP ('petnexo_docx_' + [guid]::NewGuid().ToString())

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

$body = New-Object System.Collections.Generic.List[string]
$body.Add((Add-Paragraph 'Informe de Entrega Tecnica - PetNexo / PetCare Loja' 'Title'))
$body.Add((Add-Paragraph 'Resumen detallado de cambios realizados, estado actual y pasos pendientes antes de entrega o despliegue.' 'Subtitle'))
$body.Add((Add-Paragraph ('Fecha de generacion: ' + (Get-Date -Format 'yyyy-MM-dd HH:mm'))))

$body.Add((Add-Paragraph 'Resumen ejecutivo' 'Heading1'))
$body.Add((Add-Paragraph 'Se trabajo sobre un sistema Django para gestion de peluqueria canina/veterinaria, evolucionandolo hacia una plataforma parametrizable llamada PetNexo. El proyecto incluye pagina publica, registro de clientes, agenda, mascotas, pagos, suscripciones, seguimiento, calificaciones, chatbot, panel administrativo y preparacion para despliegue en Vercel con Supabase.'))

$body.Add((Add-Paragraph 'Cambios principales realizados' 'Heading1'))
@(
    'Parametrizacion del negocio: nombre, ciudad, telefono, correo, direccion, textos publicos, moneda y marca.',
    'Mejoras visuales en formularios principales: registro, login, perfil, contacto, mascotas, servicios y agenda.',
    'Login con boton para ver u ocultar contrasena.',
    'Google OAuth preparado con variables GOOGLE_LOGIN_ENABLED, GOOGLE_CLIENT_ID y GOOGLE_CLIENT_SECRET.',
    'Boton de Google protegido para no mostrarse si faltan credenciales.',
    'Pagos de citas y suscripciones preparados con Datafast.',
    'Planes de suscripcion Basico, Pro y Premium.',
    'Separacion de roles: dueno PetNexo, administrador del local y cliente final.',
    'Panel de gestion para citas, servicios, sucursales, pagos, seguimiento y suscripcion.',
    'Seguimiento de mascota por etapas: agendada, recibida, bano, secado, corte, revision, lista y entregada.',
    'Sistema de calificaciones con estrellas y comentarios.',
    'Chatbot de asistencia basica para servicios, horarios, citas, pagos y seguimiento.',
    'Preparacion de despliegue con vercel.json, runtime.txt y api/index.py.'
) | ForEach-Object { $body.Add((Add-Bullet $_)) }

$body.Add((Add-Paragraph 'Agenda y sucursales' 'Heading1'))
$body.Add((Add-Paragraph 'La agenda fue ajustada para funcionar con varios locales. La disponibilidad se calcula por sucursal, fecha y hora. Esto significa que una hora ocupada en una sucursal no bloquea automaticamente otra sucursal.'))
@(
    'Se agregaron campos de horario por sucursal: hora_apertura, hora_cierre, intervalo_turnos y dias_cerrados.',
    'Las fechas pasadas se bloquean desde el formulario y tambien desde backend.',
    'El endpoint de disponibilidad devuelve estados como fecha_pasada, dia_cerrado, sucursal_invalida y ok.',
    'Los horarios ocupados se muestran con check y quedan deshabilitados.',
    'Se creo pantalla para crear y editar sucursales desde el sistema: gestion/sucursal/nueva/ y gestion/sucursal/<id>/editar/.'
) | ForEach-Object { $body.Add((Add-Bullet $_)) }

$body.Add((Add-Paragraph 'Archivos modificados o creados' 'Heading1'))
@(
    'citas/models.py: nuevos campos y metodos de Sucursal; ajuste de Google login configurado.',
    'citas/forms.py: validacion de agenda por sucursal y nuevo SucursalForm.',
    'citas/views.py: disponibilidad por sucursal, eliminar perfil y formulario de sucursal.',
    'citas/urls.py: rutas de perfil/eliminar y gestion de sucursales.',
    'citas/admin.py: visualizacion de campos de horario por sucursal.',
    'templates/agendar.html: rediseno y manejo de estados de disponibilidad.',
    'templates/sucursal_form.html: nueva pantalla para administrar locales.',
    'templates/perfil.html: rediseno y boton para eliminar cuenta de cliente.',
    'templates/contacto.html, registro.html, mascota_form.html y servicio_form.html: mejoras visuales.',
    'citas/migrations/0015_sucursal_horario_configurable.py: migracion nueva para horarios de sucursal.'
) | ForEach-Object { $body.Add((Add-Bullet $_)) }

$body.Add((Add-Paragraph 'Migraciones' 'Heading1'))
$body.Add((Add-Paragraph 'La migracion nueva que debe subirse y ejecutarse es citas/migrations/0015_sucursal_horario_configurable.py. Esta migracion agrega campos de horario y dias cerrados a la tabla de sucursales.'))
$body.Add((Add-Paragraph 'Comandos recomendados' 'Heading2'))
@(
    'py manage.py makemigrations --check',
    'py manage.py migrate',
    'py manage.py check',
    'py manage.py runserver 8082'
) | ForEach-Object { $body.Add((Add-Paragraph $_ 'Code')) }

$body.Add((Add-Paragraph 'Configuracion pendiente para produccion' 'Heading1'))
@(
    'DATABASE_URL debe apuntar a Supabase PostgreSQL.',
    'SECRET_KEY debe ser larga y segura.',
    'DEBUG=False en Vercel.',
    'ALLOWED_HOSTS y CSRF_TRUSTED_ORIGINS deben incluir el dominio real.',
    'GOOGLE_LOGIN_ENABLED=True, GOOGLE_CLIENT_ID y GOOGLE_CLIENT_SECRET si se usara Google.',
    'DATAFAST_ENTITY_ID y DATAFAST_AUTHORIZATION para pagos reales.',
    'Ejecutar migraciones en Supabase antes de pruebas finales.'
) | ForEach-Object { $body.Add((Add-Bullet $_)) }

$body.Add((Add-Paragraph 'Pruebas finales antes de entregar' 'Heading1'))
@(
    'Crear usuario cliente y completar perfil.',
    'Eliminar cuenta cliente desde Mi Perfil y verificar que no aplique a administradores.',
    'Crear mascota y editar ficha.',
    'Crear y editar sucursales con distintos horarios.',
    'Agendar cita en una sucursal y verificar que la misma hora siga libre en otra sucursal.',
    'Intentar agendar en fecha pasada y confirmar que el sistema lo rechaza.',
    'Verificar que los horarios ocupados salgan con check y no se puedan seleccionar.',
    'Actualizar seguimiento desde panel administrador.',
    'Registrar pago en efectivo, transferencia y tarjeta.',
    'Calificar una cita y validar que las metricas se actualicen.',
    'Probar login normal y login con Google en dominio de Vercel.',
    'Probar suscripcion mensual/anual y flujo de pago.'
) | ForEach-Object { $body.Add((Add-Bullet $_)) }

$body.Add((Add-Paragraph 'Estado actual' 'Heading1'))
$body.Add((Add-Paragraph 'El sistema tiene una base funcional avanzada para pruebas de mercado. Antes de considerarlo entregado al 100%, se debe ejecutar la migracion 0015, validar Django con py manage.py check, probar el flujo completo y configurar variables reales de Vercel, Supabase, Google y Datafast.'))

$bodyXml = $body -join "`n"
$documentXml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>' + $bodyXml + '<w:sectPr><w:pgSz w:w="12240" w:h="15840"/><w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" w:header="720" w:footer="720" w:gutter="0"/></w:sectPr></w:body></w:document>'

$contentTypes = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/><Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/><Override PartName="/word/numbering.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.numbering+xml"/></Types>'
$rels = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>'
$docRels = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/numbering" Target="numbering.xml"/></Relationships>'
$styles = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:qFormat/><w:pPr><w:spacing w:after="160" w:line="276" w:lineRule="auto"/></w:pPr><w:rPr><w:rFonts w:ascii="Aptos" w:hAnsi="Aptos"/><w:sz w:val="22"/></w:rPr></w:style><w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:basedOn w:val="Normal"/><w:qFormat/><w:pPr><w:spacing w:after="220"/></w:pPr><w:rPr><w:b/><w:color w:val="00685F"/><w:sz w:val="42"/></w:rPr></w:style><w:style w:type="paragraph" w:styleId="Subtitle"><w:name w:val="Subtitle"/><w:basedOn w:val="Normal"/><w:qFormat/><w:rPr><w:color w:val="475569"/><w:sz w:val="24"/></w:rPr></w:style><w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/><w:pPr><w:spacing w:before="360" w:after="160"/><w:outlineLvl w:val="0"/></w:pPr><w:rPr><w:b/><w:color w:val="0F172A"/><w:sz w:val="30"/></w:rPr></w:style><w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/><w:pPr><w:spacing w:before="240" w:after="120"/><w:outlineLvl w:val="1"/></w:pPr><w:rPr><w:b/><w:color w:val="00685F"/><w:sz w:val="25"/></w:rPr></w:style><w:style w:type="paragraph" w:styleId="ListParagraph"><w:name w:val="List Paragraph"/><w:basedOn w:val="Normal"/><w:pPr><w:ind w:left="720"/></w:pPr></w:style><w:style w:type="paragraph" w:styleId="Code"><w:name w:val="Code"/><w:basedOn w:val="Normal"/><w:pPr><w:spacing w:before="40" w:after="80"/><w:shd w:fill="F1F5F9"/></w:pPr><w:rPr><w:rFonts w:ascii="Consolas" w:hAnsi="Consolas"/><w:color w:val="0F172A"/><w:sz w:val="19"/></w:rPr></w:style></w:styles>'
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
