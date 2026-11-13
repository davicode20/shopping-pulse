from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.dashboard import metricas
from apps.eventos import repositorio as repo
from apps.eventos.models import Evento, Interacao
from apps.participacao.checkin import token_checkin


class FluxoParticipacaoTests(TestCase):
    def setUp(self):
        cache.clear()
        # Os dados do teste são criados aqui; não queremos a base simulada nestes testes.
        repo._pronto = True
        self.evento = repo.adicionar_evento({
            "nome": "Sexta Acústica", "categoria": "musica", "data": "2027-03-05",
            "horario": "19:00", "local": "Hall", "status": "confirmado", "informacoes": "",
        })
        self.client = Client()

    def post(self, url, dados=None):
        return self.client.post(url, dados or {})

    def interacoes(self, tipo):
        return Interacao.objects.filter(evento_id=self.evento["id"], tipo=tipo)

    # --- interesse ---

    def test_interesse_grava_no_banco_e_retorna_total(self):
        resposta = self.post(reverse("participacao:interesse"),
                             {"evento_id": self.evento["id"], "acao": "interesse"})
        self.assertEqual(resposta.status_code, 200)
        self.assertTrue(resposta.json()["interessado"])
        self.assertEqual(resposta.json()["total_interessados"], 1)
        self.assertEqual(self.interacoes(repo.INTERESSE).count(), 1)

    def test_interesse_repetido_nao_duplica(self):
        for _ in range(3):
            self.post(reverse("participacao:interesse"), {"evento_id": self.evento["id"], "acao": "interesse"})
        self.assertEqual(self.interacoes(repo.INTERESSE).count(), 1)

    def test_sem_interesse_troca_o_interesse_anterior(self):
        url = reverse("participacao:interesse")
        self.post(url, {"evento_id": self.evento["id"], "acao": "interesse"})
        self.post(url, {"evento_id": self.evento["id"], "acao": "sem_interesse"})
        self.assertEqual(self.interacoes(repo.INTERESSE).count(), 0)
        self.assertEqual(self.interacoes(repo.SEM_INTERESSE).count(), 1)

    def test_presenca_alterna_e_depende_do_interesse(self):
        url = reverse("participacao:presenca")
        self.assertTrue(self.post(url, {"evento_id": self.evento["id"]}).json()["vou"])
        self.assertEqual(self.interacoes(repo.INTERESSE).count(), 1)  # presença implica interesse
        self.assertFalse(self.post(url, {"evento_id": self.evento["id"]}).json()["vou"])
        self.assertEqual(self.interacoes(repo.PRESENCA).count(), 0)

    def test_visualizacao_e_registrada_uma_vez_por_visitante(self):
        self.post(reverse("participacao:interesse"), {"evento_id": self.evento["id"], "acao": "interesse"})
        self.post(reverse("participacao:interesse"), {"evento_id": self.evento["id"], "acao": "interesse"})
        self.assertEqual(self.interacoes(repo.VISUALIZACAO).count(), 1)

    # --- check-in ---

    def test_checkin_com_token_invalido_nao_grava(self):
        resposta = self.client.get(reverse("participacao:checkin", args=[self.evento["id"], "tokenerrado00"]))
        self.assertEqual(resposta.context["situacao"], "invalido")
        self.assertEqual(self.interacoes(repo.CHECKIN).count(), 0)

    def test_checkin_valido_grava_uma_vez(self):
        url = reverse("participacao:checkin", args=[self.evento["id"], token_checkin(self.evento["id"])])
        self.client.get(url)
        self.client.get(url)
        self.assertEqual(self.interacoes(repo.CHECKIN).count(), 1)

    # --- avaliação ---

    def test_avaliacao_exige_checkin(self):
        resposta = self.post(reverse("participacao:avaliar", args=[self.evento["id"]]), {"nota": "4"})
        self.assertTrue(resposta.context["sem_checkin"])
        self.assertEqual(self.interacoes(repo.AVALIACAO).count(), 0)

    def test_avaliacao_apos_checkin_grava_nota(self):
        url_checkin = reverse("participacao:checkin", args=[self.evento["id"], token_checkin(self.evento["id"])])
        self.client.get(url_checkin)
        url = reverse("participacao:avaliar", args=[self.evento["id"]])
        self.assertEqual(self.post(url, {"nota": "0"}).status_code, 200)  # nota fora da faixa
        self.assertEqual(self.interacoes(repo.AVALIACAO).count(), 0)
        self.post(url, {"nota": "4", "novamente": "sim", "melhorias": ["horario"], "comentario": "Bom"})
        self.post(url, {"nota": "5", "novamente": "sim"})  # vale a última avaliação
        avaliacoes = self.interacoes(repo.AVALIACAO)
        self.assertEqual(avaliacoes.count(), 1)
        self.assertEqual(avaliacoes.first().dados["nota"], 5)

    # --- proteção CSRF ---

    def test_post_sem_csrf_e_recusado(self):
        cliente = Client(enforce_csrf_checks=True)
        resposta = cliente.post(reverse("participacao:interesse"),
                                {"evento_id": self.evento["id"], "acao": "interesse"})
        self.assertEqual(resposta.status_code, 403)
        self.assertEqual(self.interacoes(repo.INTERESSE).count(), 0)


class PersistenciaTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_evento_criado_fica_gravado_no_banco(self):
        repo._pronto = True
        evento = repo.adicionar_evento({"nome": "Teste", "categoria": "cultura", "data": "2027-04-01",
                                        "horario": "10:00", "status": "proposta"})
        self.assertTrue(Evento.objects.filter(pk=evento["id"], nome="Teste").exists())

    def test_regra_de_unicidade_no_banco(self):
        repo._pronto = True
        evento = repo.adicionar_evento({"nome": "Teste", "categoria": "cultura", "data": "2027-04-01",
                                        "horario": "10:00", "status": "proposta"})
        repo.registrar_interacao(repo.INTERESSE, evento["id"], "visitante-x")
        with self.assertRaises(IntegrityError), transaction.atomic():
            Interacao.objects.create(evento_id=evento["id"], tipo=repo.INTERESSE,
                                     visitante="visitante-x", momento=timezone.now())

    def test_carregar_json_e_idempotente(self):
        repo.reiniciar()
        self.assertEqual(repo.carregar_json(), 12)
        self.assertEqual(len(repo.listar_eventos()), 12)

    def test_reiniciar_volta_ao_estado_inicial(self):
        repo.adicionar_evento({"nome": "Criado na demonstração", "categoria": "musica",
                               "data": "2027-05-01", "horario": "18:00", "status": "proposta"})
        repo.reiniciar()
        nomes = [e["nome"] for e in repo.listar_eventos()]
        self.assertEqual(len(nomes), 12)
        self.assertNotIn("Criado na demonstração", nomes)
        interacoes = repo.listar_interacoes()
        self.assertGreater(len(interacoes), 0)
        self.assertTrue(all(i["simulado"] for i in interacoes))


class PainelLeDadosPersistidosTests(TestCase):
    def setUp(self):
        cache.clear()
        from django.contrib.auth import get_user_model
        get_user_model().objects.create_user("admin-painel", password="senha-teste-123", is_staff=True)
        repo._pronto = True
        self.evento = repo.adicionar_evento({
            "nome": "Arena Gamer", "categoria": "tecnologia", "data": "2027-06-10",
            "horario": "14:00", "status": "confirmado",
        })
        self.client.post(reverse("dashboard:login"), {"usuario": "admin-painel", "senha": "senha-teste-123"})

    def test_interesse_registrado_aparece_nos_indicadores(self):
        antes = metricas.calcular_indicadores()["total_interesses"]
        Client().post(reverse("participacao:interesse"), {"evento_id": self.evento["id"], "acao": "interesse"})
        depois = metricas.calcular_indicadores()["total_interesses"]
        self.assertEqual(depois, antes + 1)

    def test_painel_responde_com_dados_persistidos(self):
        resposta = self.client.get(reverse("dashboard:dados"), HTTP_ACCEPT="application/json")
        self.assertEqual(resposta.status_code, 200)
