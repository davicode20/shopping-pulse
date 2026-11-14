# ShoppDash

> Transformando preferências em experiências. Protótipo do Hackarun Palmas.

Plataforma de engajamento e análise de experiências para shopping centers. O visitante usa uma área mobile (sem instalar app), e a administração conta com um painel de inteligência com indicadores ao vivo e recomendações geradas por IA.

🌐 **Demo online:** https://shopping-pulse.onrender.com (o plano free do Render pode levar ~1 min para acordar no primeiro acesso)

📄 **[Resumo do projeto para os avaliadores (1 página)](docs/ShoppDash-Resumo.pdf)** · **[Planejamento técnico inicial (1ª entrega)](docs/PLANEJAMENTO.md)** · **[Como rodar, passo a passo](COMO_RODAR.txt)**

**Ciclo:** PLANEJAMENTO → ENGAJAMENTO → PARTICIPAÇÃO → AVALIAÇÃO → INTELIGÊNCIA → NOVO PLANEJAMENTO

## Stack
Python + Django (templates) · HTML/CSS · Bootstrap 5 · JavaScript · Chart.js · Google Gemini · qrcode

## Como rodar

```bash
cd ~/PycharmProjects/shopping-pulse
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # se o .env ainda não existir
python manage.py migrate         # cria o banco db.sqlite3 (obrigatório antes do login)
python manage.py definir_admin   # cria o administrador do painel (usuário e senha no banco)
python manage.py runserver 0.0.0.0:8000
```

Se aparecer `no such table` ao entrar, falta o `migrate`.

Se a porta 8000 já estiver em uso, um servidor antigo pode estar respondendo no lugar do atual. Sintomas: `/participacao/conta/` dá 404, ou `/painel/` abre sem pedir senha. Para liberar a porta no Windows:

```
netstat -ano | findstr :8000
taskkill /PID <número_do_PID> /F
```

Use o número da última coluna. Ou rode em outra porta, por exemplo `python manage.py runserver 8001`.

**Login do painel:** `/painel/` pede usuário e senha de um administrador. Crie com `python manage.py definir_admin`; rode de novo para trocar a senha. Este login é separado da área do visitante.

**Conta do visitante (opcional):** em `/participacao/conta/` (ícone de pessoa no topo da área do visitante) é possível criar uma conta ou entrar. Ao entrar, as interações feitas antes no mesmo navegador passam para a conta. A área do visitante continua aberta sem conta.

**Dados:** eventos e interações ficam no banco `db.sqlite3`, na raiz do projeto, que não vai para o Git. O botão **Reiniciar dados** volta aos eventos do `data/eventos.json` e à base simulada. Para atualizar só os eventos a partir do JSON, sem apagar nada, use `python manage.py carregar_eventos`.

Para expor a demo fora da rede local (ex.: ngrok), use `DJANGO_DEBUG=False` e uma `DJANGO_SECRET_KEY` própria: com `DEBUG=False`, o servidor se recusa a subir com a chave de exemplo.

| Área | Endereço |
|---|---|
| Visitante (celular) | http://127.0.0.1:8000/ |
| Painel administrativo (com login) | http://127.0.0.1:8000/painel/ |
| Análise da IA (JSON) | http://127.0.0.1:8000/inteligencia/analise/ |

**Celular na mesma rede Wi-Fi:** acesse `http://IP-DO-PC:8000/`. O QR Code de check-in já troca `localhost` pelo IP da rede automaticamente. Se precisar, fixe o endereço com `URL_PUBLICA` no `.env`.

**Miro:** coloque `MIRO_ACCESS_TOKEN` (app em developers.miro.com com escopo `boards:write`) e `MIRO_BOARD_ID` (ID ou link do quadro) no `.env`. O botão **Exportar para o Miro** cria no quadro um frame com a análise: resumo, destaques, recomendações (sticky notes coloridos por prioridade), eventos sugeridos (cards), validação de demanda e alertas. Sem token, o botão vira **Baixar para o Miro (CSV)**, para importar manualmente.

**IA real:** coloque a chave em `GEMINI_API_KEY` no `.env` (gere em https://aistudio.google.com/apikey). O modelo padrão é o `gemini-3.5-flash` (cerca de 20 s por análise); se ele estiver sobrecarregado, o painel tenta os modelos de `GEMINI_MODELOS_RESERVA` (padrão: `gemini-3.5-flash-lite`). Sem chave, ou se nenhum modelo responder, o painel usa o **modo demonstração**: recomendações por regras, geradas a partir dos mesmos números calculados.

**Checagem dos números:** a resposta da IA tem formato garantido por schema, e cada número citado é conferido com os dados enviados (`apps/inteligencia/verificacao.py`). O painel mostra "N de N números conferidos" e destaca em amarelo qualquer número que não exista nos dados.

## Deploy (link público)

O projeto está pronto para o **Render** (`render.yaml` na raiz):

1. Em [render.com](https://render.com), entre com o GitHub → **New → Blueprint** → escolha este repositório.
2. Preencha as variáveis pedidas: `ADMIN_USUARIO`, `ADMIN_SENHA_HASH` (gere com `python manage.py definir_admin --hash`; o admin é recriado a partir dessas duas variáveis a cada inicialização), `GEMINI_API_KEY`, `MIRO_ACCESS_TOKEN` e `MIRO_BOARD_ID`.
3. **Apply**. Em alguns minutos o sistema fica em `https://shopping-pulse.onrender.com` (ou nome parecido).

Pontos importantes:
- **Sem banco externo:** os dados ficam num SQLite local, recriado a cada deploy ou reinício (volta à base simulada). O login do painel sobrevive, porque a sessão fica num cookie assinado. Um processo só (`--workers 1`), pois o cache da análise da IA fica em memória.
- **IA pronta ao subir:** a análise é gerada em segundo plano assim que o servidor inicia, para o painel não esperar o Gemini no primeiro acesso.
- **Plano free:** o serviço dorme após 15 min sem acesso; o primeiro acesso depois disso leva cerca de 1 min e os dados voltam ao estado inicial (base simulada). Para a apresentação, use o plano Starter ou abra o link alguns minutos antes.
- Em produção (`DJANGO_DEBUG=False`) o WhiteNoise serve CSS/JS, os cookies só trafegam por HTTPS e o endereço público entra sozinho em `ALLOWED_HOSTS` e `CSRF_TRUSTED_ORIGINS`.

## Funcionalidades

### Visitante (mobile first)
- **Início:** próximos eventos, filtro por categoria, recomendações ("Para você" / "Em alta").
- **Descobrir:** cartões estilo swipe (direita = quero, esquerda = passo; também funciona com as setas ← → do teclado).
- **Ajude a decidir:** votação em ideias de eventos ainda não confirmadas (validação de demanda).
- **Detalhe do evento:** "Tenho interesse" e "Pretendo ir" (presença provável).
- **Check-in por QR Code:** link com token assinado (HMAC) por evento.
- **Avaliação pós-evento:** estrelas, "participaria de novo?", pontos de melhoria e comentário (exige check-in).
- **Minha agenda:** interesses, experiências vividas e recomendações.
- Faixa etária **opcional e anônima**, usada na validação de demanda.

### Administração
- **Painel ao vivo** (atualiza a cada 5 s): KPIs, evolução do engajamento, interesse por categoria, top eventos, atividade recente, validação de demanda e desempenho por evento.
- **Recomendações da IA:** resumo, destaques, recomendações priorizadas, eventos sugeridos e alertas, com um painel de transparência mostrando os dados enviados à IA.
- **Exportar para o Miro:** a análise vira um frame no quadro da equipe (um frame novo a cada exportação, lado a lado), o que fecha o ciclo Inteligência → Novo planejamento.
- **Eventos:** cadastro (em validação ou confirmado) com pré-visualização do celular.
- **Detalhe do evento:** funil de participação, faixa etária, notas, melhorias, comentários e o QR Code de check-in.
- **Ferramentas da demonstração:** simular +150 visitantes, simular a realização do evento e reiniciar os dados.

## Roteiro da apresentação (≈ 5 min)

1. **Painel** (`/painel/`): "o shopping hoje decide no escuro; aqui ele enxerga o visitante". Mostre os KPIs e os gráficos.
2. **Validação de demanda:** o *Festival Sabores do Tocantins* (R$ 15 mil) teve 1.200 visualizações, 840 interessados e 320 presenças prováveis, com 65% do público entre 18 e 30 anos. "Validamos antes de investir."
3. **Novo evento** → publique uma ideia ao vivo (ex.: *Festival do Açaí*).
4. **Celular** (projete ou passe para os avaliadores): abra o site, escolha a faixa etária e deslize os cartões. O novo evento aparece. **No painel, o contador "interações reais" e a atividade recente mudam na hora.**
5. No detalhe do evento, clique em **Simular +150 visitantes** para mostrar a escala.
6. **O evento acontece:** escaneie o QR Code da tela com o celular → check-in confirmado (confete 🎉) → **avaliação**.
7. **Recomendações da IA** → "Gerar nova análise" (leva cerca de 20 s: gere uma vez antes de apresentar). Destaque que a IA **não inventa números**: os indicadores são calculados pela aplicação, a IA apenas interpreta, e o selo verde mostra que **cada número citado foi conferido** com os dados (abra também o painel de transparência).
8. **Exportar para o Miro** → abra o quadro: "a recomendação já vira o planejamento da equipe".
9. Feche com o ciclo e a visão de SaaS.

> Dica: antes de apresentar, entre no painel, clique em **Reiniciar dados** na barra lateral e gere uma análise da IA.

## Decisões do protótipo
- **Banco SQLite (D-004).** Eventos e interações ficam no banco, pelo ORM do Django (`apps/eventos/models.py`, `apps/eventos/repositorio.py`). Há uma interação por tipo e visitante por evento, exceto visualização. As sessões ficam num cookie assinado, para o login sobreviver aos reinícios do servidor no Render.
- **Dados simulados identificados.** A base histórica é gerada por `apps/eventos/simulacao.py` (semente fixa, sempre igual). Toda interação tem a flag `simulado`, e o painel mostra quantas interações são reais.
- **Números calculados pela aplicação** (`apps/dashboard/metricas.py`). A IA só interpreta (`apps/inteligencia/servico.py`).
- **IA com plano B:** se o Gemini não responder, as recomendações por regras usam os mesmos indicadores.
- **Bibliotecas locais** em `static/vendor/` (Bootstrap, Icons, Chart.js): a demo não depende da internet do evento. Só a fonte Poppins vem do Google Fonts, com fallback para a fonte do sistema.
- **Nome configurável:** altere `NOME_PROJETO` no `.env` (Circulaê, Nexora, Vibraê...).
- **Login pelo `django.contrib.auth`.** Administradores são usuários com `is_staff`, criados com `definir_admin` (`apps/dashboard/acesso.py`). Sessão de 12 h em cookie assinado, bloqueio após 5 tentativas erradas e "Gerar nova análise" limitado a uma chamada a cada 15 s. As views usam o decorator `@admin_requerido`. Visitantes têm conta própria (`apps/participacao/contas.py`), sem acesso ao painel.

## Estrutura
```
config/            settings, urls, context processor (nome/slogan)
apps/
  eventos/         área do visitante, modelos e repositório (SQLite), simulação, filtros de template
  participacao/    interesse, presença, check-in (QR + token), avaliação, conta do visitante
  dashboard/       painel, métricas, cadastro de eventos, QR Code, ferramentas da demo
  inteligencia/    Gemini + análise por regras (plano B) + exportação para o Miro
data/              eventos.json
templates/         visitante/ e administrativo/
static/            css/, js/ (main, swipe, painel), vendor/
```
