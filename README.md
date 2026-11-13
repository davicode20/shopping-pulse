# Shopping Pulse

> Transformando preferências em experiências. Protótipo do Hackarun Palmas.

Plataforma de engajamento e análise de experiências para shopping centers. O visitante usa uma área mobile (sem instalar app), e a administração conta com um painel de inteligência com indicadores ao vivo e recomendações geradas por IA.

📄 **[Planejamento técnico inicial (1ª entrega)](docs/PLANEJAMENTO.md)**

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
python manage.py runserver 0.0.0.0:8000
```

| Área | Endereço |
|---|---|
| Visitante (celular) | http://127.0.0.1:8000/ |
| Painel administrativo | http://127.0.0.1:8000/painel/ |
| Análise da IA (JSON) | http://127.0.0.1:8000/inteligencia/analise/ |

**Celular na mesma rede Wi-Fi:** acesse `http://IP-DO-PC:8000/`. O QR Code de check-in já troca `localhost` pelo IP da rede automaticamente. Se precisar, fixe o endereço com `URL_PUBLICA` no `.env`.

**Miro:** coloque `MIRO_ACCESS_TOKEN` (app em developers.miro.com com escopo `boards:write`) e `MIRO_BOARD_ID` (ID ou link do quadro) no `.env`. O botão **Exportar para o Miro** cria no quadro um frame com a análise: resumo, destaques, recomendações (sticky notes coloridos por prioridade), eventos sugeridos (cards), validação de demanda e alertas. Sem token, o botão vira **Baixar para o Miro (CSV)**, para importar manualmente.

**IA real:** coloque a chave em `GEMINI_API_KEY` no `.env` (gere em https://aistudio.google.com/apikey). O modelo padrão é o `gemini-3.5-flash` (cerca de 20 s por análise); se ele estiver sobrecarregado, o painel tenta os modelos de `GEMINI_MODELOS_RESERVA` (padrão: `gemini-3.5-flash-lite`). Sem chave, ou se nenhum modelo responder, o painel usa o **modo demonstração**: recomendações por regras, geradas a partir dos mesmos números calculados.

**Checagem dos números:** a resposta da IA tem formato garantido por schema, e cada número citado é conferido com os dados enviados (`apps/inteligencia/verificacao.py`). O painel mostra "N de N números conferidos" e destaca em amarelo qualquer número que não exista nos dados.

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

> Dica: antes de apresentar, clique em **Reiniciar dados** na barra lateral.

## Decisões do protótipo
- **Sem banco de dados.** Os eventos vêm de `data/eventos.json` e as interações ficam em memória (`apps/eventos/repositorio.py`). Ao reiniciar o servidor, os dados voltam ao estado inicial. As sessões usam cookies assinados, então não há `migrate`.
- **Dados simulados identificados.** A base histórica é gerada por `apps/eventos/simulacao.py` (semente fixa, sempre igual). Toda interação tem a flag `simulado`, e o painel mostra quantas interações são reais.
- **Números calculados pela aplicação** (`apps/dashboard/metricas.py`). A IA só interpreta (`apps/inteligencia/servico.py`).
- **IA com plano B:** se o Gemini não responder, as recomendações por regras usam os mesmos indicadores.
- **Bibliotecas locais** em `static/vendor/` (Bootstrap, Icons, Chart.js): a demo não depende da internet do evento. Só a fonte Poppins vem do Google Fonts, com fallback para a fonte do sistema.
- **Nome configurável:** altere `NOME_PROJETO` no `.env` (Circulaê, Nexora, Vibraê...).
- **Sem login no painel.** Para o protótipo, isso é aceitável; em produção, usaríamos o `django.contrib.auth`.

## Estrutura
```
config/            settings, urls, context processor (nome/slogan)
apps/
  eventos/         área do visitante, repositório em memória, simulação, filtros de template
  participacao/    interesse, presença, check-in (QR + token), avaliação
  dashboard/       painel, métricas, cadastro de eventos, QR Code, ferramentas da demo
  inteligencia/    Gemini + análise por regras (plano B) + exportação para o Miro
data/              eventos.json
templates/         visitante/ e administrativo/
static/            css/, js/ (main, swipe, painel), vendor/
```
