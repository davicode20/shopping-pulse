from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from apps.eventos import repositorio

SENHA = "senha-de-teste-123"


class AcessoAdministrativoTests(TestCase):
    def setUp(self):
        cache.clear()  # o limite de tentativas usa o cache
        modelo = get_user_model()
        self.admin = modelo.objects.create_user("admin-teste", password=SENHA, is_staff=True)
        self.visitante = modelo.objects.create_user("visitante-teste", password=SENHA, is_staff=False)

    def entrar(self, usuario, senha=SENHA):
        return self.client.post(reverse("dashboard:login"), {"usuario": usuario, "senha": senha})

    # --- acesso anônimo ---

    def test_painel_redireciona_para_login(self):
        resposta = self.client.get(reverse("dashboard:painel"))
        self.assertEqual(resposta.status_code, 302)
        self.assertIn(reverse("dashboard:login"), resposta["Location"])

    def test_dados_json_exige_login(self):
        resposta = self.client.get(reverse("dashboard:dados"), HTTP_ACCEPT="application/json")
        self.assertEqual(resposta.status_code, 401)

    def test_inteligencia_exige_login(self):
        resposta = self.client.get(reverse("inteligencia:analise"))
        self.assertEqual(resposta.status_code, 302)
        self.assertIn(reverse("dashboard:login"), resposta["Location"])

    def test_reiniciar_anonimo_nao_executa(self):
        evento = repositorio.adicionar_evento({"nome": "Evento de teste", "categoria": "musica",
                                               "data": "2027-02-01", "horario": "19:00", "status": "proposta"})
        resposta = self.client.post(reverse("dashboard:reiniciar"))
        self.assertEqual(resposta.status_code, 302)
        self.assertIsNotNone(repositorio.obter_evento(evento["id"]))

    # --- login ---

    def test_login_de_administrador_libera_o_painel(self):
        resposta = self.entrar("admin-teste")
        self.assertEqual(resposta.status_code, 302)
        self.assertEqual(self.client.get(reverse("dashboard:painel")).status_code, 200)

    def test_visitante_nao_entra_na_area_administrativa(self):
        resposta = self.entrar("visitante-teste")
        self.assertEqual(resposta.status_code, 401)
        self.assertEqual(self.client.get(reverse("dashboard:painel")).status_code, 302)

    def test_senha_errada_retorna_erro_generico(self):
        resposta = self.entrar("admin-teste", senha="errada")
        self.assertEqual(resposta.status_code, 401)
        self.assertContains(resposta, "Usuário ou senha incorretos.", status_code=401)

    def test_limite_de_tentativas_bloqueia_novas_tentativas(self):
        for _ in range(5):
            self.entrar("admin-teste", senha="errada")
        resposta = self.entrar("admin-teste")  # senha certa, mas bloqueada
        self.assertContains(resposta, "Muitas tentativas", status_code=401)

    def test_redirecionamento_externo_e_recusado(self):
        resposta = self.client.post(reverse("dashboard:login"),
                                    {"usuario": "admin-teste", "senha": SENHA, "proximo": "https://exemplo.com"})
        self.assertEqual(resposta["Location"], reverse("dashboard:painel"))

    # --- logout ---

    def test_logout_encerra_a_sessao_no_servidor(self):
        self.entrar("admin-teste")
        self.client.post(reverse("dashboard:logout"))
        self.assertEqual(self.client.get(reverse("dashboard:painel")).status_code, 302)

    def test_logout_por_get_nao_e_permitido(self):
        self.entrar("admin-teste")
        self.assertEqual(self.client.get(reverse("dashboard:logout")).status_code, 405)

    def test_logout_preserva_o_visitante_anonimo(self):
        self.client.get("/descobrir/")  # cria o identificador anônimo do visitante
        visitante = self.client.session.get("visitante_id")
        self.assertIsNotNone(visitante)
        self.entrar("admin-teste")
        self.client.post(reverse("dashboard:logout"))
        self.assertEqual(self.client.session.get("visitante_id"), visitante)

    # --- administrador criado pelo comando ---

    def test_comando_definir_admin_cria_conta_de_equipe(self):
        from django.core.management import call_command
        from unittest import mock

        with mock.patch("getpass.getpass", side_effect=[SENHA, SENHA]):
            call_command("definir_admin", "--usuario", "novo-admin")
        conta = get_user_model().objects.get(username="novo-admin")
        self.assertTrue(conta.is_staff)
        self.assertFalse(conta.is_superuser)
        self.assertTrue(conta.check_password(SENHA))
