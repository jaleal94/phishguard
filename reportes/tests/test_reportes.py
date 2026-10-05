"""Pruebas de la app reportes (RF-22 a RF-25 y RF-30)."""

from datetime import timedelta
from unittest import mock

from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from panel.models import Bitacora
from reportes import servicios
from reportes.models import ReporteSospechoso
from simulaciones.models import Campana, Destinatario, EventoSimulacion, PlantillaCorreo
from usuarios.tests.utilidades import crear_admin, crear_usuario

SUPABASE = {"SUPABASE_URL": "https://demo.supabase.co", "SUPABASE_SERVICE_KEY": "clave"}
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 64
PDF = b"%PDF-1.7\n" + b"0" * 64


def datos_reporte(**extra):
    datos = {
        "remitente": "Soporte <soporte@ejemplo.com>",
        "asunto": "Verifique su cuenta",
        "fecha_recepcion": (timezone.localtime() - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M"),
        "descripcion": "Me pidió la contraseña.",
    }
    datos.update(extra)
    return datos


def crear_reporte(usuario, **campos):
    campos.setdefault("remitente", "x@ejemplo.com")
    campos.setdefault("asunto", "Asunto")
    campos.setdefault("fecha_recepcion", timezone.now())
    return ReporteSospechoso.objects.create(reportado_por=usuario, **campos)


class AdjuntoTests(TestCase):
    """RF-22: tipos permitidos, tamaño máximo y subida a Supabase Storage."""

    def setUp(self):
        self.usuario = crear_usuario()
        self.client.force_login(self.usuario)
        self.url = reverse("reportes:reportar")

    def _enviar(self, nombre, contenido, tipo="application/octet-stream"):
        archivo = SimpleUploadedFile(nombre, contenido, content_type=tipo)
        return self.client.post(self.url, {**datos_reporte(), "adjunto": archivo})

    def test_reporte_sin_adjunto(self):
        r = self.client.post(self.url, datos_reporte())
        reporte = ReporteSospechoso.objects.get()
        self.assertRedirects(r, reverse("reportes:detalle", args=[reporte.pk]))
        self.assertEqual(reporte.reportado_por, self.usuario)
        self.assertEqual(reporte.estado, ReporteSospechoso.Estado.PENDIENTE)

    def test_rechaza_extension_no_permitida(self):
        for nombre in ("virus.exe", "documento.docx", "pagina.html", "comprimido.zip"):
            with self.subTest(archivo=nombre):
                r = self._enviar(nombre, b"MZ" + b"0" * 10)
                self.assertIn("adjunto", r.context["form"].errors)
        self.assertFalse(ReporteSospechoso.objects.exists())

    def test_rechaza_archivo_renombrado(self):
        r = self._enviar("factura.pdf", b"MZ\x90\x00 ejecutable")
        self.assertIn("no corresponde", str(r.context["form"].errors["adjunto"]))

    @override_settings(REPORTE_TAMANO_MAX_MB=1)
    def test_rechaza_archivo_que_supera_el_tamano(self):
        r = self._enviar("captura.png", PNG + b"0" * (1024 * 1024))
        self.assertIn("tamaño máximo", str(r.context["form"].errors["adjunto"]))

    @override_settings(**SUPABASE)
    def test_sube_adjuntos_permitidos_al_bucket_privado(self):
        archivos = [
            ("captura.png", PNG), ("foto.jpg", b"\xff\xd8\xff\xe0" + b"0" * 32),
            ("correo.pdf", PDF), ("mensaje.eml", b"From: a@b.com\nSubject: x\n\nHola"),
        ]
        with mock.patch("phishguard.almacenamiento.requests.post") as post:
            post.return_value.status_code = 200
            for nombre, contenido in archivos:
                with self.subTest(archivo=nombre):
                    self._enviar(nombre, contenido)
        self.assertEqual(ReporteSospechoso.objects.count(), 4)
        for reporte in ReporteSospechoso.objects.all():
            self.assertTrue(reporte.adjunto_url.startswith("reportes/"))
        url_subida = post.call_args.args[0]
        self.assertIn("/storage/v1/object/phishguard/reportes/", url_subida)

    def test_sin_almacenamiento_configurado_no_guarda_el_reporte(self):
        r = self._enviar("captura.png", PNG, "image/png")
        self.assertIn("No se pudo guardar el adjunto", str(r.context["form"].errors["adjunto"]))
        self.assertFalse(ReporteSospechoso.objects.exists())

    def test_fecha_futura_no_permitida(self):
        futura = (timezone.localtime() + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M")
        r = self.client.post(self.url, datos_reporte(fecha_recepcion=futura))
        self.assertIn("fecha_recepcion", r.context["form"].errors)


class AtencionTests(TestCase):
    """RF-23 y RF-24: cambio de estado, bitácora y notificación."""

    def setUp(self):
        self.admin = crear_admin()
        self.colaborador = crear_usuario()
        self.reporte = crear_reporte(self.colaborador)
        self.client.force_login(self.admin)
        self.url = reverse("reportes:atender", args=[self.reporte.pk])

    def test_cambio_de_estado_queda_en_bitacora_con_el_administrador(self):
        self.client.post(
            self.url, {"estado": "PHISHING_CONFIRMADO", "comentario": "Bloqueamos el dominio."}
        )
        self.reporte.refresh_from_db()
        self.assertEqual(self.reporte.estado, "PHISHING_CONFIRMADO")
        self.assertEqual(self.reporte.atendido_por, self.admin)
        self.assertIsNotNone(self.reporte.atendido_en)
        registro = Bitacora.objects.get(accion="CAMBIO_ESTADO_REPORTE")
        self.assertEqual(registro.usuario, self.admin)
        self.assertEqual(registro.detalle["antes"], "PENDIENTE")
        self.assertEqual(registro.detalle["despues"], "PHISHING_CONFIRMADO")

    def test_colaborador_recibe_correo_y_ve_el_estado_en_su_panel(self):
        self.client.post(self.url, {"estado": "FALSO_POSITIVO", "comentario": "Es legítimo."})
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.colaborador.email])
        self.assertIn("Falso positivo", mail.outbox[0].subject)
        self.assertIn("Es legítimo.", mail.outbox[0].body)
        self.client.force_login(self.colaborador)
        r = self.client.get(reverse("panel:mi_panel"))
        self.assertContains(r, "Falso positivo")

    def test_sin_cambio_de_estado_no_notifica(self):
        self.client.post(self.url, {"estado": "PENDIENTE", "comentario": "Revisando"})
        self.assertEqual(len(mail.outbox), 0)
        self.assertFalse(Bitacora.objects.filter(accion="CAMBIO_ESTADO_REPORTE").exists())

    def test_error_smtp_no_impide_el_cambio(self):
        with mock.patch("reportes.servicios.send_mail", side_effect=OSError("smtp caído")):
            self.client.post(self.url, {"estado": "EN_REVISION", "comentario": ""})
        self.reporte.refresh_from_db()
        self.assertEqual(self.reporte.estado, "EN_REVISION")

    @override_settings(**SUPABASE)
    def test_descarga_de_adjunto_con_url_firmada(self):
        self.reporte.adjunto_url = "reportes/abc.pdf"
        self.reporte.save()
        with mock.patch("phishguard.almacenamiento.requests.post") as post:
            post.return_value.json.return_value = {"signedURL": "/object/sign/phishguard/x?t=1"}
            post.return_value.raise_for_status.return_value = None
            r = self.client.post(reverse("reportes:descargar_adjunto", args=[self.reporte.pk]))
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r.url, "https://demo.supabase.co/storage/v1/object/sign/phishguard/x?t=1")

    def test_filtro_por_estado_en_la_bandeja(self):
        crear_reporte(self.colaborador, asunto="Otro", estado="EN_REVISION")
        r = self.client.get(reverse("reportes:bandeja"), {"estado": "EN_REVISION"})
        self.assertEqual([x.asunto for x in r.context["pagina"]], ["Otro"])


class VinculoCampanaTests(TestCase):
    """RF-25: el reporte de un correo de campaña crea un EventoSimulacion REPORTE."""

    def setUp(self):
        self.usuario = crear_usuario()
        plantilla = PlantillaCorreo.objects.create(
            nombre="Prueba",
            asunto="Actualice sus datos de nómina",
            remitente_visible="Recursos Humanos <rrhh@curex-nomina.com>",
            cuerpo_html="<p>Plantilla de prueba</p>",
        )
        self.campana = Campana.objects.create(
            nombre="Campaña 1", plantilla=plantilla, estado=Campana.Estado.FINALIZADA
        )
        self.destinatario = Destinatario.objects.create(
            campana=self.campana, usuario=self.usuario, enviado_en=timezone.now()
        )

    def _reportar(self, usuario=None, **campos):
        campos.setdefault("asunto", "Actualice sus datos de nómina")
        campos.setdefault("remitente", "rrhh@curex-nomina.com")
        reporte = crear_reporte(usuario or self.usuario, **campos)
        return reporte, servicios.vincular_con_campana(reporte)

    def eventos(self):
        return EventoSimulacion.objects.filter(tipo=EventoSimulacion.Tipo.REPORTE)

    def test_coincidencia_crea_evento_reporte(self):
        reporte, destinatario = self._reportar()
        self.assertEqual(destinatario, self.destinatario)
        reporte.refresh_from_db()
        self.assertTrue(reporte.es_simulacion)
        self.assertEqual(self.eventos().get().destinatario, self.destinatario)

    def test_ignora_prefijos_mayusculas_y_nombre_del_remitente(self):
        _, destinatario = self._reportar(
            asunto="RV: ACTUALICE  sus datos de nómina",
            remitente="Recursos Humanos <RRHH@curex-nomina.com>",
        )
        self.assertEqual(destinatario, self.destinatario)

    def test_reportar_dos_veces_no_duplica_el_evento(self):
        self._reportar()
        self._reportar()
        self.assertEqual(self.eventos().count(), 1)

    def test_asunto_distinto_no_vincula(self):
        _, destinatario = self._reportar(asunto="Factura pendiente")
        self.assertIsNone(destinatario)
        self.assertFalse(self.eventos().exists())

    def test_remitente_distinto_no_vincula(self):
        _, destinatario = self._reportar(remitente="rrhh@curex.net.ve")
        self.assertIsNone(destinatario)

    def test_campana_de_otro_usuario_no_vincula(self):
        _, destinatario = self._reportar(usuario=crear_usuario("otro@curex.net.ve"))
        self.assertIsNone(destinatario)

    def test_campana_programada_o_correo_no_enviado_no_vincula(self):
        self.campana.estado = Campana.Estado.PROGRAMADA
        self.campana.save()
        self.assertIsNone(self._reportar()[1])
        self.campana.estado = Campana.Estado.ENVIANDO
        self.campana.save()
        self.destinatario.enviado_en = None
        self.destinatario.save()
        self.assertIsNone(self._reportar()[1])

    def test_vinculo_desde_el_formulario(self):
        self.client.force_login(self.usuario)
        self.client.post(
            reverse("reportes:reportar"),
            datos_reporte(
                asunto="Actualice sus datos de nómina",
                remitente="Recursos Humanos <rrhh@curex-nomina.com>",
            ),
        )
        self.assertEqual(self.eventos().count(), 1)
        reporte = ReporteSospechoso.objects.get()
        r = self.client.get(reverse("reportes:detalle", args=[reporte.pk]))
        self.assertContains(r, "Bien hecho")


class PrivacidadYPermisosTests(TestCase):
    """RF-30 y RF-04/05."""

    def setUp(self):
        self.colaborador = crear_usuario()
        self.otro = crear_usuario("otro@curex.net.ve")
        self.reporte_ajeno = crear_reporte(self.otro, asunto="Reporte ajeno")

    def test_rf30_no_ve_reportes_de_otro_usuario(self):
        self.client.force_login(self.colaborador)
        r = self.client.get(reverse("reportes:detalle", args=[self.reporte_ajeno.pk]))
        self.assertEqual(r.status_code, 404)
        r = self.client.get(reverse("panel:mi_panel"))
        self.assertNotContains(r, "Reporte ajeno")
        r = self.client.get(reverse("reportes:reportar"))
        self.assertNotContains(r, "Reporte ajeno")

    def test_colaborador_recibe_403_en_vistas_administrativas(self):
        self.client.force_login(self.colaborador)
        pk = self.reporte_ajeno.pk
        vistas = [
            ("reportes:bandeja", [], "get"),
            ("reportes:atender", [pk], "get"),
            ("reportes:atender", [pk], "post"),
            ("reportes:descargar_adjunto", [pk], "post"),
        ]
        for nombre, args, metodo in vistas:
            with self.subTest(vista=nombre, metodo=metodo):
                r = getattr(self.client, metodo)(reverse(nombre, args=args))
                self.assertEqual(r.status_code, 403)

    def test_admin_accede_a_bandeja_y_detalle(self):
        self.client.force_login(crear_admin())
        self.assertEqual(self.client.get(reverse("reportes:bandeja")).status_code, 200)
        r = self.client.get(reverse("reportes:atender", args=[self.reporte_ajeno.pk]))
        self.assertEqual(r.status_code, 200)

    def test_admin_tambien_puede_reportar(self):
        self.client.force_login(crear_admin())
        r = self.client.post(reverse("reportes:reportar"), datos_reporte())
        self.assertEqual(r.status_code, 302)
