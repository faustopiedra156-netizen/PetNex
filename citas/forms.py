from django import forms
from django.conf import settings
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.models import User
from django.utils import timezone
from .models import (
    Mascota, PerfilCliente, Cita, Servicio, Calificacion, ConfiguracionNegocio,
    Sucursal, SuscripcionNegocio, Negocio, UsuarioNegocio, MensajeContacto,
)
import datetime

def parse_hora_config(valor, default):
    try:
        return datetime.time.fromisoformat(str(valor))
    except (TypeError, ValueError):
        return default


HORA_APERTURA = parse_hora_config(settings.APPOINTMENT_OPEN_TIME, datetime.time(8, 30))
HORA_CIERRE = parse_hora_config(settings.APPOINTMENT_CLOSE_TIME, datetime.time(18, 30))
SLOT_MINUTES = max(int(settings.APPOINTMENT_SLOT_MINUTES or 30), 1)
MINUTOS_PERMITIDOS = set(range(0, 60, SLOT_MINUTES))
DIAS_CERRADOS = set(settings.APPOINTMENT_CLOSED_WEEKDAYS)


class EmailOrUsernameAuthenticationForm(AuthenticationForm):
    error_messages = {
        'invalid_login': 'Ingresa un usuario o correo electrónico y una contraseña válidos.',
        'inactive': 'Esta cuenta está inactiva.',
    }

    def clean(self):
        identifier = (self.cleaned_data.get('username') or '').strip()
        if identifier:
            matching_users = list(
                User.objects.filter(
                    email__iexact=identifier,
                    is_active=True,
                ).only('username')[:2]
            )
            if len(matching_users) == 1:
                self.cleaned_data['username'] = matching_users[0].get_username()
        return super().clean()


def generar_horarios():
    horarios = []
    hora = datetime.datetime.combine(datetime.date.today(), HORA_APERTURA)
    cierre = datetime.datetime.combine(datetime.date.today(), HORA_CIERRE)
    while hora <= cierre:
        value = hora.time().strftime('%H:%M')
        horarios.append((value, value))
        hora += datetime.timedelta(minutes=SLOT_MINUTES)
    return horarios


def generar_horarios_sucursal(sucursal):
    if sucursal:
        return [(hora.strftime('%H:%M'), hora.strftime('%H:%M')) for hora in sucursal.generar_horarios()]
    return generar_horarios()


class MascotaForm(forms.ModelForm):
    MAX_FOTO_BYTES = 5 * 1024 * 1024

    class Meta:
        model = Mascota
        fields = ['nombre', 'especie', 'raza', 'edad', 'peso_kg', 'notas_medicas', 'foto']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-300 focus:ring-2 focus:ring-[#00685f] focus:border-transparent outline-none transition', 'placeholder': 'Ej. Firulais'}),
            'especie': forms.TextInput(attrs={'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-300 focus:ring-2 focus:ring-[#00685f] focus:border-transparent outline-none transition', 'placeholder': 'Canino / Felino'}),
            'raza': forms.TextInput(attrs={'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-300 focus:ring-2 focus:ring-[#00685f] focus:border-transparent outline-none transition', 'placeholder': 'Ej. Poodle, Schnauzer, Mestizo'}),
            'edad': forms.NumberInput(attrs={'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-300 focus:ring-2 focus:ring-[#00685f] focus:border-transparent outline-none transition', 'min': 0, 'max': 30}),
            'peso_kg': forms.NumberInput(attrs={'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-300 focus:ring-2 focus:ring-[#00685f] focus:border-transparent outline-none transition', 'step': '0.5'}),
            'notas_medicas': forms.Textarea(attrs={'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-300 focus:ring-2 focus:ring-[#00685f] focus:border-transparent outline-none transition', 'rows': 3, 'placeholder': 'Alergias, sensible a ruidos, temperamento...'}),
            'foto': forms.ClearableFileInput(attrs={
                'class': 'block w-full text-sm text-slate-600 file:mr-4 file:rounded-xl file:border-0 file:bg-teal-50 file:px-4 file:py-2.5 file:font-bold file:text-[#00685f] hover:file:bg-teal-100',
                'accept': 'image/jpeg,image/png,image/webp',
            }),
        }

    def clean_foto(self):
        foto = self.cleaned_data.get('foto')
        if foto and foto.size > self.MAX_FOTO_BYTES:
            raise forms.ValidationError('La foto no puede superar los 5 MB.')
        return foto

    def clean_edad(self):
        edad = self.cleaned_data.get('edad')
        if edad is not None and not 0 <= edad <= 30:
            raise forms.ValidationError('La edad debe estar entre 0 y 30 años.')
        return edad

    def clean_peso_kg(self):
        peso = self.cleaned_data.get('peso_kg')
        if peso is not None and not 0.1 <= peso <= 200:
            raise forms.ValidationError('El peso debe estar entre 0,1 y 200 kg.')
        return peso


class CitaForm(forms.ModelForm):
    class Meta:
        model = Cita
        fields = ['sucursal', 'mascota', 'servicio', 'fecha', 'hora', 'notas']
        widgets = {
            'sucursal': forms.Select(attrs={'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-300 focus:ring-2 focus:ring-[#00685f] focus:border-transparent outline-none transition'}),
            'mascota': forms.Select(attrs={'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-300 focus:ring-2 focus:ring-[#00685f] focus:border-transparent outline-none transition'}),
            'servicio': forms.Select(attrs={'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-300 focus:ring-2 focus:ring-[#00685f] focus:border-transparent outline-none transition'}),
            'fecha': forms.DateInput(attrs={'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-300 focus:ring-2 focus:ring-[#00685f] focus:border-transparent outline-none transition', 'type': 'date', 'lang': 'es'}),
            'hora': forms.HiddenInput(attrs={'id': 'id_hora'}),
            'notas': forms.Textarea(attrs={'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-300 focus:ring-2 focus:ring-[#00685f] focus:border-transparent outline-none transition', 'rows': 2, 'placeholder': 'Requerimientos especiales para el baño o corte...'}),
        }

    def __init__(self, user, *args, **kwargs):
        negocio = kwargs.pop('negocio', None)
        self.user = user
        self.negocio = negocio
        super().__init__(*args, **kwargs)
        self.fields['fecha'].widget.attrs['min'] = timezone.localdate().isoformat()
        if user and user.is_authenticated:
            mascotas = Mascota.objects.filter(propietario=user)
            if negocio:
                mascotas = mascotas.filter(negocio=negocio)
            else:
                mascotas = mascotas.none()
            self.fields['mascota'].queryset = mascotas.select_related('propietario').only(
                'nombre', 'raza', 'negocio',
                'propietario__username', 'propietario__first_name', 'propietario__last_name'
            )
        sucursales = Sucursal.objects.filter(activa=True)
        servicios = Servicio.objects.filter(activo=True)
        if negocio:
            sucursales = sucursales.filter(negocio=negocio)
            servicios = servicios.filter(negocio=negocio)
        self.fields['sucursal'].queryset = sucursales.only('nombre', 'ciudad', 'direccion', 'negocio')
        self.fields['servicio'].queryset = servicios.only('nombre', 'precio', 'negocio')
        self.fields['sucursal'].label = 'Sucursal'
        self.fields['mascota'].label = 'Mascota'
        self.fields['servicio'].label = 'Servicio solicitado'
        self.fields['fecha'].label = 'Fecha de atenci\u00f3n'
        self.fields['hora'].label = 'Hora preferida'
        self.fields['notas'].label = 'Observaciones o notas adicionales'
        self.fields['sucursal'].empty_label = 'Selecciona una sucursal'
        self.fields['mascota'].empty_label = 'Selecciona una mascota'
        self.fields['servicio'].empty_label = 'Selecciona un servicio'
        self.fields['sucursal'].error_messages['required'] = "Selecciona la sucursal donde se atender\u00e1 la mascota."
        self.fields['mascota'].error_messages['required'] = "Selecciona una mascota registrada."
        self.fields['servicio'].error_messages['required'] = "Selecciona el servicio que deseas reservar."
        self.fields['fecha'].error_messages['required'] = "Selecciona la fecha de atenci\u00f3n."
        self.fields['hora'].error_messages['required'] = "Selecciona una hora disponible en la agenda."

    def clean_fecha(self):
        fecha = self.cleaned_data.get('fecha')
        if not fecha:
            return fecha
        if fecha < timezone.localdate():
            raise forms.ValidationError("No puedes agendar una cita en una fecha pasada.")
        sucursal = self.cleaned_data.get('sucursal')
        if sucursal and not sucursal.atiende_en_fecha(fecha):
            raise forms.ValidationError("La sucursal no atiende en la fecha seleccionada. Elige otro d\u00eda.")
        if not sucursal and fecha.weekday() in DIAS_CERRADOS:
            raise forms.ValidationError("El negocio no atiende en la fecha seleccionada. Elige otro d\u00eda.")
        return fecha

    def clean_hora(self):
        hora = self.cleaned_data.get('hora')
        if not hora:
            return hora
        sucursal = self.cleaned_data.get('sucursal')
        if sucursal:
            horarios_permitidos = set(sucursal.generar_horarios())
            apertura = sucursal.hora_apertura
            cierre = sucursal.hora_cierre
        else:
            horarios_permitidos = {datetime.time.fromisoformat(value) for value, _ in generar_horarios()}
            apertura = HORA_APERTURA
            cierre = HORA_CIERRE
        if hora not in horarios_permitidos:
            raise forms.ValidationError(f"Selecciona un horario disponible entre {apertura.strftime('%H:%M')} y {cierre.strftime('%H:%M')}.")
        return hora

    def clean(self):
        cleaned_data = super().clean()
        fecha = cleaned_data.get('fecha')
        hora = cleaned_data.get('hora')
        sucursal = cleaned_data.get('sucursal')
        mascota = cleaned_data.get('mascota')
        servicio = cleaned_data.get('servicio')
        if self.negocio:
            if mascota and mascota.negocio_id != self.negocio.id:
                self.add_error('mascota', 'Selecciona una mascota registrada en este local.')
            if sucursal and sucursal.negocio_id != self.negocio.id:
                self.add_error('sucursal', 'Selecciona una sucursal de este local.')
            if servicio and servicio.negocio_id != self.negocio.id:
                self.add_error('servicio', 'Selecciona un servicio de este local.')
        if sucursal and fecha and hora:
            existe = Cita.objects.filter(sucursal=sucursal, fecha=fecha, hora=hora).exclude(estado='CANCELADA')
            if self.instance and self.instance.pk:
                existe = existe.exclude(pk=self.instance.pk)
            if existe.exists():
                raise forms.ValidationError("Ese horario ya est\u00e1 ocupado en la sucursal seleccionada. Elige otra hora.")
        return cleaned_data


class AdminUsuarioForm(forms.ModelForm):
    negocio_nombre = forms.CharField(widget=forms.TextInput(attrs={'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-[#00685f] outline-none', 'placeholder': 'Ej. Happy Pets Quito'}))
    telefono = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-[#00685f] outline-none', 'placeholder': '+593 99 999 9999'}))
    direccion = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-[#00685f] outline-none', 'placeholder': 'Direcci\u00f3n de referencia'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'id': 'adminPasswordInput', 'class': 'w-full px-4 py-2.5 pr-12 rounded-xl border border-slate-300 focus:ring-2 focus:ring-[#00685f] outline-none', 'placeholder': 'Contrase\u00f1a temporal'}))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={'id': 'adminConfirmPasswordInput', 'class': 'w-full px-4 py-2.5 pr-12 rounded-xl border border-slate-300 focus:ring-2 focus:ring-[#00685f] outline-none', 'placeholder': 'Confirmar contrase\u00f1a'}))

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'username']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-[#00685f] outline-none', 'placeholder': 'Nombre'}),
            'last_name': forms.TextInput(attrs={'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-[#00685f] outline-none', 'placeholder': 'Apellido'}),
            'email': forms.EmailInput(attrs={'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-[#00685f] outline-none', 'placeholder': 'correo@ejemplo.com'}),
            'username': forms.TextInput(attrs={'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-[#00685f] outline-none', 'placeholder': 'usuario'}),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip()
        if email and User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Ya existe una cuenta con este correo.")
        return email

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()
        if username and User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("Ya existe una cuenta con este usuario.")
        return username

    def clean_password(self):
        password = self.cleaned_data.get('password')
        if not password:
            return password
        validate_password(password, self.instance)
        return password

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('password') != cleaned_data.get('confirm_password'):
            raise forms.ValidationError("Las contrase\u00f1as no coinciden.")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        user.is_staff = True
        user.is_superuser = False
        if commit:
            user.save()
            negocio, _ = Negocio.objects.get_or_create(
                propietario=user,
                defaults={'nombre': self.cleaned_data['negocio_nombre']},
            )
            if negocio.nombre != self.cleaned_data['negocio_nombre']:
                negocio.nombre = self.cleaned_data['negocio_nombre']
                negocio.save(update_fields=['nombre'])
            PerfilCliente.objects.get_or_create(
                usuario=user,
                defaults={
                    'negocio': negocio,
                    'telefono': self.cleaned_data.get('telefono', ''),
                    'direccion': self.cleaned_data.get('direccion', ''),
                },
            )
            UsuarioNegocio.objects.get_or_create(
                usuario=user,
                negocio=negocio,
                defaults={'rol': 'ADMIN_LOCAL'},
            )
        return user


class ServicioForm(forms.ModelForm):
    class Meta:
        model = Servicio
        fields = ['nombre', 'categoria', 'descripcion', 'precio', 'duracion_minutos', 'icono', 'destacado', 'activo']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-[#00685f] outline-none', 'placeholder': 'Ej. Baño & Spa Canino Pro'}),
            'categoria': forms.Select(attrs={'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-[#00685f] outline-none bg-white'}),
            'descripcion': forms.Textarea(attrs={'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-[#00685f] outline-none', 'rows': 4, 'placeholder': 'Describe lo que incluye el servicio.'}),
            'precio': forms.NumberInput(attrs={'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-[#00685f] outline-none', 'min': '0', 'step': '0.01'}),
            'duracion_minutos': forms.NumberInput(attrs={'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-[#00685f] outline-none', 'min': '5', 'step': '5'}),
            'icono': forms.TextInput(attrs={'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-[#00685f] outline-none', 'placeholder': 'content_cut, pets, shower, health_and_safety'}),
            'destacado': forms.CheckboxInput(attrs={'class': 'h-4 w-4 rounded border-slate-300 text-[#00685f]'}),
            'activo': forms.CheckboxInput(attrs={'class': 'h-4 w-4 rounded border-slate-300 text-[#00685f]'}),
        }


class SucursalForm(forms.ModelForm):
    class Meta:
        model = Sucursal
        fields = ['nombre', 'ciudad', 'direccion', 'telefono', 'hora_apertura', 'hora_cierre', 'intervalo_turnos', 'dias_cerrados', 'activa']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-[#00685f] outline-none', 'placeholder': 'Ej. Sucursal norte'}),
            'ciudad': forms.TextInput(attrs={'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-[#00685f] outline-none', 'placeholder': 'Loja'}),
            'direccion': forms.TextInput(attrs={'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-[#00685f] outline-none', 'placeholder': 'Direcci\u00f3n exacta'}),
            'telefono': forms.TextInput(attrs={'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-[#00685f] outline-none', 'placeholder': '+593 99 999 9999'}),
            'hora_apertura': forms.TimeInput(attrs={'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-[#00685f] outline-none', 'type': 'time'}),
            'hora_cierre': forms.TimeInput(attrs={'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-[#00685f] outline-none', 'type': 'time'}),
            'intervalo_turnos': forms.NumberInput(attrs={'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-[#00685f] outline-none', 'min': '5', 'step': '5'}),
            'dias_cerrados': forms.TextInput(attrs={'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-[#00685f] outline-none', 'placeholder': '6'}),
            'activa': forms.CheckboxInput(attrs={'class': 'h-4 w-4 rounded border-slate-300 text-[#00685f]'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        apertura = cleaned_data.get('hora_apertura')
        cierre = cleaned_data.get('hora_cierre')
        if apertura and cierre and apertura >= cierre:
            raise forms.ValidationError("La hora de apertura debe ser menor que la hora de cierre.")
        return cleaned_data

    def clean_intervalo_turnos(self):
        intervalo = self.cleaned_data.get('intervalo_turnos')
        if intervalo is None:
            return intervalo
        if intervalo < 5 or intervalo > 180:
            raise forms.ValidationError("El intervalo debe estar entre 5 y 180 minutos.")
        return intervalo

    def clean_dias_cerrados(self):
        valor = self.cleaned_data.get('dias_cerrados', '')
        dias = []
        for item in str(valor).split(','):
            item = item.strip()
            if not item:
                continue
            if not item.isdigit() or int(item) not in range(7):
                raise forms.ValidationError("Usa n\u00fameros del 0 al 6 separados por coma.")
            dias.append(str(int(item)))
        return ','.join(dict.fromkeys(dias))


class PerfilClienteForm(forms.ModelForm):
    first_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-300 focus:ring-2 focus:ring-[#00685f]', 'placeholder': 'Nombre'})
    )
    last_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-300 focus:ring-2 focus:ring-[#00685f]', 'placeholder': 'Apellido'})
    )
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-300 focus:ring-2 focus:ring-[#00685f]', 'placeholder': 'correo@ejemplo.com'})
    )

    class Meta:
        model = PerfilCliente
        fields = ['telefono', 'direccion', 'barrio', 'contacto_preferido']
        widgets = {
            'telefono': forms.TextInput(attrs={'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-300 focus:ring-2 focus:ring-[#00685f]', 'placeholder': '+593 99 999 9999'}),
            'direccion': forms.TextInput(attrs={'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-300 focus:ring-2 focus:ring-[#00685f]', 'placeholder': 'Direcci\u00f3n de referencia'}),
            'barrio': forms.TextInput(attrs={'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-300 focus:ring-2 focus:ring-[#00685f]', 'placeholder': 'Barrio o sector'}),
            'contacto_preferido': forms.Select(attrs={'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-300 focus:ring-2 focus:ring-[#00685f]'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        super().__init__(*args, **kwargs)
        self.fields['contacto_preferido'].label = 'Medio de contacto preferido'
        self.fields['contacto_preferido'].choices = [
            ('whatsapp', 'WhatsApp'),
            ('llamada', 'Llamada telefónica'),
            ('email', 'Correo electrónico'),
        ]
        self.fields['first_name'].initial = self.user.first_name
        self.fields['last_name'].initial = self.user.last_name
        self.fields['email'].initial = self.user.email

    def save(self, commit=True):
        perfil = super().save(commit=False)
        self.user.first_name = self.cleaned_data.get('first_name', '')
        self.user.last_name = self.cleaned_data.get('last_name', '')
        self.user.email = self.cleaned_data.get('email', '')
        if commit:
            self.user.save()
            perfil.save()
        return perfil

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if email and User.objects.filter(email__iexact=email).exclude(pk=self.user.pk).exists():
            raise forms.ValidationError('Ya existe otra cuenta con este correo.')
        return email


class ConfiguracionNegocioForm(forms.ModelForm):
    class Meta:
        model = ConfiguracionNegocio
        fields = [
            'nombre', 'nombre_corto', 'ciudad', 'pais', 'codigo_pais', 'categoria',
            'slogan', 'hero_badge', 'hero_titulo', 'hero_descripcion', 'contacto_titulo', 'contacto_descripcion', 'descripcion_footer',
            'email', 'telefono', 'direccion', 'latitud', 'longitud', 'horario', 'moneda', 'simbolo_moneda',
            'etiqueta_resenas', 'etiqueta_ubicacion', 'texto_boton_principal',
            'prefijo_transaccion', 'mostrar_cuentas_demo', 'google_login_activo',
        ]
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'w-full px-3 py-2 rounded-xl border border-slate-300'}),
            'nombre_corto': forms.TextInput(attrs={'class': 'w-full px-3 py-2 rounded-xl border border-slate-300'}),
            'ciudad': forms.TextInput(attrs={'class': 'w-full px-3 py-2 rounded-xl border border-slate-300'}),
            'pais': forms.TextInput(attrs={'class': 'w-full px-3 py-2 rounded-xl border border-slate-300'}),
            'codigo_pais': forms.TextInput(attrs={'class': 'w-full px-3 py-2 rounded-xl border border-slate-300', 'maxlength': '2'}),
            'categoria': forms.TextInput(attrs={'class': 'w-full px-3 py-2 rounded-xl border border-slate-300'}),
            'slogan': forms.TextInput(attrs={'class': 'w-full px-3 py-2 rounded-xl border border-slate-300'}),
            'hero_badge': forms.TextInput(attrs={'class': 'w-full px-3 py-2 rounded-xl border border-slate-300'}),
            'hero_titulo': forms.TextInput(attrs={'class': 'w-full px-3 py-2 rounded-xl border border-slate-300'}),
            'hero_descripcion': forms.Textarea(attrs={'class': 'w-full px-3 py-2 rounded-xl border border-slate-300', 'rows': 3}),
            'contacto_titulo': forms.TextInput(attrs={'class': 'w-full px-3 py-2 rounded-xl border border-slate-300'}),
            'contacto_descripcion': forms.Textarea(attrs={'class': 'w-full px-3 py-2 rounded-xl border border-slate-300', 'rows': 3}),
            'descripcion_footer': forms.Textarea(attrs={'class': 'w-full px-3 py-2 rounded-xl border border-slate-300', 'rows': 3}),
            'email': forms.EmailInput(attrs={'class': 'w-full px-3 py-2 rounded-xl border border-slate-300'}),
            'telefono': forms.TextInput(attrs={'class': 'w-full px-3 py-2 rounded-xl border border-slate-300'}),
            'direccion': forms.TextInput(attrs={'class': 'w-full px-3 py-2 rounded-xl border border-slate-300'}),
            'latitud': forms.HiddenInput(),
            'longitud': forms.HiddenInput(),
            'horario': forms.TextInput(attrs={'class': 'w-full px-3 py-2 rounded-xl border border-slate-300'}),
            'moneda': forms.TextInput(attrs={'class': 'w-full px-3 py-2 rounded-xl border border-slate-300'}),
            'simbolo_moneda': forms.TextInput(attrs={'class': 'w-full px-3 py-2 rounded-xl border border-slate-300'}),
            'etiqueta_resenas': forms.TextInput(attrs={'class': 'w-full px-3 py-2 rounded-xl border border-slate-300'}),
            'etiqueta_ubicacion': forms.TextInput(attrs={'class': 'w-full px-3 py-2 rounded-xl border border-slate-300'}),
            'texto_boton_principal': forms.TextInput(attrs={'class': 'w-full px-3 py-2 rounded-xl border border-slate-300'}),
            'prefijo_transaccion': forms.TextInput(attrs={'class': 'w-full px-3 py-2 rounded-xl border border-slate-300'}),
            'mostrar_cuentas_demo': forms.CheckboxInput(attrs={'class': 'h-4 w-4 rounded border-slate-300 text-[#00685f]'}),
            'google_login_activo': forms.CheckboxInput(attrs={'class': 'h-4 w-4 rounded border-slate-300 text-[#00685f]'}),
        }


class SuscripcionNegocioForm(forms.ModelForm):
    class Meta:
        model = SuscripcionNegocio
        fields = ['plan', 'estado', 'fecha_inicio', 'fecha_vencimiento', 'contacto_pago', 'notas']
        widgets = {
            'plan': forms.Select(attrs={'class': 'w-full px-3 py-2 rounded-xl border border-slate-300'}),
            'estado': forms.Select(attrs={'class': 'w-full px-3 py-2 rounded-xl border border-slate-300'}),
            'fecha_inicio': forms.DateInput(attrs={'class': 'w-full px-3 py-2 rounded-xl border border-slate-300', 'type': 'date'}),
            'fecha_vencimiento': forms.DateInput(attrs={'class': 'w-full px-3 py-2 rounded-xl border border-slate-300', 'type': 'date'}),
            'contacto_pago': forms.TextInput(attrs={'class': 'w-full px-3 py-2 rounded-xl border border-slate-300', 'placeholder': 'WhatsApp o correo para renovacion'}),
            'notas': forms.Textarea(attrs={'class': 'w-full px-3 py-2 rounded-xl border border-slate-300', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['plan'].label = 'Plan de suscripción'
        self.fields['estado'].label = 'Estado de la suscripción'
        self.fields['plan'].empty_label = 'Selecciona un plan'
        self.fields['fecha_inicio'].label = 'Fecha de inicio'
        self.fields['fecha_vencimiento'].label = 'Fecha de vencimiento'
        self.fields['contacto_pago'].label = 'Contacto para pagos'
        self.fields['notas'].label = 'Notas internas'


class CalificacionForm(forms.ModelForm):
    class Meta:
        model = Calificacion
        fields = ['puntuacion', 'comentario']
        widgets = {
            'puntuacion': forms.RadioSelect(attrs={'class': 'sr-only'}),
            'comentario': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-300 focus:ring-2 focus:ring-[#00685f] focus:border-transparent outline-none transition',
                'rows': 4,
                'placeholder': 'Cu\u00e9ntanos c\u00f3mo fue la atenci\u00f3n, el resultado del corte o cualquier detalle importante.',
            }),
        }


class SolicitarCodigoRecuperacionForm(forms.Form):
    email = forms.EmailField(
        label="Correo electronico",
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-4 py-2.5 pr-12 rounded-xl border border-slate-300 focus:ring-2 focus:ring-[#00685f] focus:border-transparent outline-none transition text-sm',
            'placeholder': 'correo@ejemplo.com',
            'autocomplete': 'email',
        }),
    )


class VerificarCodigoRecuperacionForm(forms.Form):
    codigo = forms.CharField(
        label="Codigo de verificacion",
        min_length=6,
        max_length=6,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 rounded-xl border border-slate-300 text-center font-mono text-xl tracking-[0.35em] focus:ring-2 focus:ring-[#00685f] focus:border-transparent outline-none transition',
            'placeholder': '000000',
            'inputmode': 'numeric',
            'autocomplete': 'one-time-code',
            'maxlength': '6',
        }),
    )

    def clean_codigo(self):
        codigo = self.cleaned_data['codigo'].strip()
        if not codigo.isdigit() or len(codigo) != 6:
            raise forms.ValidationError("Ingresa el codigo de seis digitos que recibiste por correo.")
        return codigo


class NuevaContrasenaRecuperacionForm(forms.Form):
    nueva_contrasena = forms.CharField(
        label="Nueva contrasena",
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-[#00685f] focus:border-transparent outline-none transition text-sm',
            'placeholder': 'Nueva contrasena',
            'autocomplete': 'new-password',
        }),
    )
    confirmar_contrasena = forms.CharField(
        label="Confirmar contrasena",
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-[#00685f] focus:border-transparent outline-none transition text-sm',
            'placeholder': 'Confirma tu contrasena',
            'autocomplete': 'new-password',
        }),
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_nueva_contrasena(self):
        password = self.cleaned_data['nueva_contrasena']
        validate_password(password, self.user)
        return password

    def clean(self):
        cleaned_data = super().clean()
        if (
            cleaned_data.get('nueva_contrasena')
            and cleaned_data.get('confirmar_contrasena')
            and cleaned_data['nueva_contrasena'] != cleaned_data['confirmar_contrasena']
        ):
            self.add_error('confirmar_contrasena', "Las contrasenas no coinciden.")
        return cleaned_data


class RegistroForm(forms.ModelForm):
    telefono = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-300 focus:ring-2 focus:ring-[#00685f]', 'placeholder': '+593 99 999 9999'}))
    direccion = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-300 focus:ring-2 focus:ring-[#00685f]', 'placeholder': 'Direcci\u00f3n de referencia'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-300 focus:ring-2 focus:ring-[#00685f] focus:border-transparent outline-none transition', 'placeholder': 'Contrase\u00f1a'}))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-300 focus:ring-2 focus:ring-[#00685f] focus:border-transparent outline-none transition', 'placeholder': 'Confirmar Contrase\u00f1a'}))

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'username']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-300 focus:ring-2 focus:ring-[#00685f]', 'placeholder': 'Nombre'}),
            'last_name': forms.TextInput(attrs={'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-300 focus:ring-2 focus:ring-[#00685f]', 'placeholder': 'Apellido'}),
            'email': forms.EmailInput(attrs={'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-300 focus:ring-2 focus:ring-[#00685f]', 'placeholder': 'correo@ejemplo.com'}),
            'username': forms.TextInput(attrs={'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-300 focus:ring-2 focus:ring-[#00685f]', 'placeholder': 'Nombre de usuario'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")
        if password != confirm_password:
            raise forms.ValidationError("Las contrase\u00f1as no coinciden.")
        if password:
            validate_password(password, self.instance)
        return cleaned_data

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('Ya existe una cuenta con este correo.')
        return email

    def clean_username(self):
        username = self.cleaned_data['username'].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError('Ya existe una cuenta con este usuario.')
        return username


class ContactoForm(forms.ModelForm):
    class Meta:
        model = MensajeContacto
        fields = ['nombre', 'telefono', 'mensaje']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'w-full px-4 py-3 rounded-xl border border-gray-300 focus:ring-2 focus:ring-[#00685f] focus:border-[#00685f] outline-none', 'placeholder': 'Tu nombre completo', 'autocomplete': 'name'}),
            'telefono': forms.TextInput(attrs={'class': 'w-full px-4 py-3 rounded-xl border border-gray-300 focus:ring-2 focus:ring-[#00685f] focus:border-[#00685f] outline-none', 'placeholder': '+593 99 999 9999', 'autocomplete': 'tel'}),
            'mensaje': forms.Textarea(attrs={'class': 'w-full px-4 py-3 rounded-xl border border-gray-300 focus:ring-2 focus:ring-[#00685f] focus:border-[#00685f] outline-none resize-none', 'rows': 6, 'placeholder': 'Cuéntanos qué necesita tu mascota'}),
        }

    def clean_telefono(self):
        telefono = ''.join(char for char in self.cleaned_data['telefono'] if char.isdigit() or char == '+')
        if len(telefono.replace('+', '')) < 7:
            raise forms.ValidationError('Ingresa un número de teléfono válido.')
        return telefono
