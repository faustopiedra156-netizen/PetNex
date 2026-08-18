from django import forms
from django.conf import settings
from django.contrib.auth.models import User
from .models import (
    Mascota, PerfilCliente, Cita, Servicio, Calificacion, ConfiguracionNegocio,
    Sucursal, SuscripcionNegocio, Negocio,
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


def generar_horarios():
    horarios = []
    hora = datetime.datetime.combine(datetime.date.today(), HORA_APERTURA)
    cierre = datetime.datetime.combine(datetime.date.today(), HORA_CIERRE)
    while hora <= cierre:
        value = hora.time().strftime('%H:%M')
        horarios.append((value, value))
        hora += datetime.timedelta(minutes=SLOT_MINUTES)
    return horarios


class MascotaForm(forms.ModelForm):
    class Meta:
        model = Mascota
        fields = ['nombre', 'especie', 'raza', 'edad', 'peso_kg', 'notas_medicas', 'foto_url']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-300 focus:ring-2 focus:ring-[#00685f] focus:border-transparent outline-none transition', 'placeholder': 'Ej. Firulais'}),
            'especie': forms.TextInput(attrs={'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-300 focus:ring-2 focus:ring-[#00685f] focus:border-transparent outline-none transition', 'placeholder': 'Canino / Felino'}),
            'raza': forms.TextInput(attrs={'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-300 focus:ring-2 focus:ring-[#00685f] focus:border-transparent outline-none transition', 'placeholder': 'Ej. Poodle, Schnauzer, Mestizo'}),
            'edad': forms.NumberInput(attrs={'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-300 focus:ring-2 focus:ring-[#00685f] focus:border-transparent outline-none transition', 'min': 0, 'max': 30}),
            'peso_kg': forms.NumberInput(attrs={'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-300 focus:ring-2 focus:ring-[#00685f] focus:border-transparent outline-none transition', 'step': '0.5'}),
            'notas_medicas': forms.Textarea(attrs={'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-300 focus:ring-2 focus:ring-[#00685f] focus:border-transparent outline-none transition', 'rows': 3, 'placeholder': 'Alergias, sensible a ruidos, temperamento...'}),
            'foto_url': forms.URLInput(attrs={'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-300 focus:ring-2 focus:ring-[#00685f] focus:border-transparent outline-none transition', 'placeholder': 'https://ejemplo.com/foto.jpg'}),
        }


class CitaForm(forms.ModelForm):
    class Meta:
        model = Cita
        fields = ['sucursal', 'mascota', 'servicio', 'fecha', 'hora', 'notas']
        widgets = {
            'sucursal': forms.Select(attrs={'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-300 focus:ring-2 focus:ring-[#00685f] focus:border-transparent outline-none transition'}),
            'mascota': forms.Select(attrs={'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-300 focus:ring-2 focus:ring-[#00685f] focus:border-transparent outline-none transition'}),
            'servicio': forms.Select(attrs={'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-300 focus:ring-2 focus:ring-[#00685f] focus:border-transparent outline-none transition'}),
            'fecha': forms.DateInput(attrs={'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-300 focus:ring-2 focus:ring-[#00685f] focus:border-transparent outline-none transition', 'type': 'date'}),
            'hora': forms.HiddenInput(attrs={'id': 'id_hora'}),
            'notas': forms.Textarea(attrs={'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-300 focus:ring-2 focus:ring-[#00685f] focus:border-transparent outline-none transition', 'rows': 2, 'placeholder': 'Requerimientos especiales para el baño o corte...'}),
        }

    def __init__(self, user, *args, **kwargs):
        negocio = kwargs.pop('negocio', None)
        self.user = user
        self.negocio = negocio
        super().__init__(*args, **kwargs)
        if user and user.is_authenticated:
            self.fields['mascota'].queryset = Mascota.objects.filter(propietario=user).select_related('propietario').only('nombre', 'raza', 'propietario__username', 'propietario__first_name', 'propietario__last_name')
        sucursales = Sucursal.objects.filter(activa=True)
        servicios = Servicio.objects.filter(activo=True)
        if negocio:
            sucursales = sucursales.filter(negocio=negocio)
            servicios = servicios.filter(negocio=negocio)
        self.fields['sucursal'].queryset = sucursales.only('nombre', 'ciudad', 'direccion')
        self.fields['servicio'].queryset = servicios.only('nombre', 'precio')
        self.fields['sucursal'].error_messages['required'] = "Selecciona la sucursal donde se atendera la mascota."
        self.fields['mascota'].error_messages['required'] = "Selecciona una mascota registrada."
        self.fields['servicio'].error_messages['required'] = "Selecciona el servicio que deseas reservar."
        self.fields['fecha'].error_messages['required'] = "Selecciona la fecha de atencion."
        self.fields['hora'].error_messages['required'] = "Selecciona una hora disponible en la agenda."

    def clean_fecha(self):
        fecha = self.cleaned_data['fecha']
        if fecha < datetime.date.today():
            raise forms.ValidationError("No puedes agendar una cita en una fecha pasada.")
        if fecha.weekday() in DIAS_CERRADOS:
            raise forms.ValidationError("El negocio no atiende en la fecha seleccionada. Elige otro dia.")
        return fecha

    def clean_hora(self):
        hora = self.cleaned_data['hora']
        if hora < HORA_APERTURA or hora > HORA_CIERRE:
            raise forms.ValidationError(f"El horario de atencion es de {HORA_APERTURA.strftime('%H:%M')} a {HORA_CIERRE.strftime('%H:%M')}.")
        if hora.minute not in MINUTOS_PERMITIDOS:
            raise forms.ValidationError(f"Agenda en bloques de {SLOT_MINUTES} minutos.")
        return hora

    def clean(self):
        cleaned_data = super().clean()
        fecha = cleaned_data.get('fecha')
        hora = cleaned_data.get('hora')
        sucursal = cleaned_data.get('sucursal')
        if sucursal and fecha and hora:
            existe = Cita.objects.filter(sucursal=sucursal, fecha=fecha, hora=hora).exclude(estado='CANCELADA')
            if self.instance and self.instance.pk:
                existe = existe.exclude(pk=self.instance.pk)
            if existe.exists():
                raise forms.ValidationError("Ese horario ya esta ocupado en la sucursal seleccionada. Elige otra hora.")
        return cleaned_data


class AdminUsuarioForm(forms.ModelForm):
    negocio_nombre = forms.CharField(widget=forms.TextInput(attrs={'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-[#00685f] outline-none', 'placeholder': 'Ej. Happy Pets Quito'}))
    telefono = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-[#00685f] outline-none', 'placeholder': '+593 99 999 9999'}))
    direccion = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-[#00685f] outline-none', 'placeholder': 'Direccion de referencia'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-[#00685f] outline-none', 'placeholder': 'Contrasena temporal'}))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-[#00685f] outline-none', 'placeholder': 'Confirmar contrasena'}))

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

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('password') != cleaned_data.get('confirm_password'):
            raise forms.ValidationError("Las contrasenas no coinciden.")
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
        return user


class ServicioForm(forms.ModelForm):
    class Meta:
        model = Servicio
        fields = ['nombre', 'categoria', 'descripcion', 'precio', 'duracion_minutos', 'icono', 'destacado', 'activo']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-[#00685f] outline-none', 'placeholder': 'Ej. Bano & Spa Canino Pro'}),
            'categoria': forms.Select(attrs={'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-[#00685f] outline-none bg-white'}),
            'descripcion': forms.Textarea(attrs={'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-[#00685f] outline-none', 'rows': 4, 'placeholder': 'Describe lo que incluye el servicio.'}),
            'precio': forms.NumberInput(attrs={'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-[#00685f] outline-none', 'min': '0', 'step': '0.01'}),
            'duracion_minutos': forms.NumberInput(attrs={'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-[#00685f] outline-none', 'min': '5', 'step': '5'}),
            'icono': forms.TextInput(attrs={'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-[#00685f] outline-none', 'placeholder': 'content_cut, pets, shower, health_and_safety'}),
            'destacado': forms.CheckboxInput(attrs={'class': 'h-4 w-4 rounded border-slate-300 text-[#00685f]'}),
            'activo': forms.CheckboxInput(attrs={'class': 'h-4 w-4 rounded border-slate-300 text-[#00685f]'}),
        }


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
            'direccion': forms.TextInput(attrs={'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-300 focus:ring-2 focus:ring-[#00685f]', 'placeholder': 'Dirección de referencia'}),
            'barrio': forms.TextInput(attrs={'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-300 focus:ring-2 focus:ring-[#00685f]', 'placeholder': 'Barrio o sector'}),
            'contacto_preferido': forms.Select(attrs={'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-300 focus:ring-2 focus:ring-[#00685f]'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        super().__init__(*args, **kwargs)
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


class ConfiguracionNegocioForm(forms.ModelForm):
    class Meta:
        model = ConfiguracionNegocio
        fields = [
            'nombre', 'nombre_corto', 'ciudad', 'pais', 'codigo_pais', 'categoria',
            'slogan', 'hero_badge', 'hero_titulo', 'hero_descripcion', 'contacto_titulo', 'contacto_descripcion', 'descripcion_footer',
            'email', 'telefono', 'direccion', 'horario', 'moneda', 'simbolo_moneda',
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


class CalificacionForm(forms.ModelForm):
    class Meta:
        model = Calificacion
        fields = ['puntuacion', 'comentario']
        widgets = {
            'puntuacion': forms.RadioSelect(attrs={'class': 'sr-only'}),
            'comentario': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-300 focus:ring-2 focus:ring-[#00685f] focus:border-transparent outline-none transition',
                'rows': 4,
                'placeholder': 'Cuéntanos cómo fue la atención, el resultado del corte o cualquier detalle importante.',
            }),
        }


class RegistroForm(forms.ModelForm):
    telefono = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-300 focus:ring-2 focus:ring-[#00685f]', 'placeholder': '+593 99 999 9999'}))
    direccion = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-300 focus:ring-2 focus:ring-[#00685f]', 'placeholder': 'Direccion de referencia'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-300 focus:ring-2 focus:ring-[#00685f] focus:border-transparent outline-none transition', 'placeholder': 'Contraseña'}))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-300 focus:ring-2 focus:ring-[#00685f] focus:border-transparent outline-none transition', 'placeholder': 'Confirmar Contraseña'}))

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
            raise forms.ValidationError("Las contraseñas no coinciden.")
        return cleaned_data
