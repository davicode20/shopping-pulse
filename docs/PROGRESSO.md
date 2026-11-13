# Progresso do Projeto Shopping Pulse

> Documento de acompanhamento. Atualize conforme as entregas forem verificadas.

## Objetivo do MVP
Entregar um fluxo funcional de descoberta de eventos, manifestação de interesse e visualização de indicadores pela administração do shopping.

## Funcionalidades identificadas na versão inicial
- [x] Feed de descoberta de eventos (implementação inicial)
- [x] Interação de interesse e votação (implementação inicial)
- [x] Painel administrativo com indicadores (implementação inicial)
- [x] Integração prevista com Gemini (depende de configuração e validação)

> Itens marcados indicam implementação identificada, não validação completa por testes.

### Persistência (decisão D-004, SQLite)
- [x] Banco SQLite configurado e migrations aplicadas (`cc2a9db`)
- [x] Modelos `Evento` e `Interacao`, com restrição de uma interação por tipo e visitante (`2f06f30`)
- [x] Repositório migrado para o ORM, mantendo as funções públicas
- [x] Eventos e interações persistem entre reinícios (verificado entre dois processos)
- [x] Comando `carregar_eventos` para atualizar os eventos a partir do JSON
- [x] "Reiniciar demonstração" volta aos 12 eventos do JSON e à base simulada
- [ ] Permitir login opcional de visitantes (exige decidir a ligação entre `Interacao` e o usuário)

### Autenticação do administrador (Etapa 4, `5345b35`)
- [x] Administrador é um usuário do Django com `is_staff`, criado com `python manage.py definir_admin`
- [x] Login com `authenticate()`/`login()`; sessões no banco, então o logout invalida a sessão no servidor
- [x] Todas as views administrativas (painel, dados, eventos, QR Code, simulação, reinício, análise da IA e exportação) exigem login no backend
- [x] Logout só por POST, e preserva o identificador do visitante anônimo
- [x] 13 testes de acesso em `apps/dashboard/tests.py`, todos passando
- [ ] Ainda não há administrador no banco de desenvolvimento: rodar `python manage.py definir_admin`
- [ ] Decisão P-002 (autenticação nativa do Django) aguarda confirmação da equipe no `DECISOES.md`

## Pendências prioritárias
- [ ] Validar o fluxo completo de ponta a ponta no navegador (login, simulações, check-in por QR, avaliação)
- [ ] Criar testes automatizados dos fluxos de persistência e participação
- [ ] Validar indicadores e integração com IA
- [ ] Revisar usabilidade e responsividade
- [ ] Atualizar `PLANEJAMENTO.md`, que ainda lista o login da administração como "Futura" e a persistência como "Futura"

## Próxima entrega sugerida
Validar o fluxo completo no navegador (criar administrador, simulações, check-in por QR, avaliação) e decidir sobre o login de visitantes.

## Registro de atualizações
| Data | Alteração | Responsável | Evidência |
|---|---|---|---|
| 2026-11-13 | Aprovada a decisão D-004: SQLite como banco do MVP | Equipe | `9763127` (docs movidos para o repositório) |
| 2026-11-13 | Configuração do SQLite e dos apps de autenticação do Django | Equipe | `cc2a9db` |
| 2026-11-13 | Modelos `Evento` e `Interacao`, repositório via ORM e comando `carregar_eventos` | Equipe | `2f06f30`; verificação manual |
| 2026-11-13 | Autenticação do administrador pelo `User` do Django, sessões no banco e testes de acesso | Equipe | `5345b35`; 13 testes passando |

## Impedimentos e riscos
- A base de demonstração é gerada na primeira execução (cerca de 16.600 interações simuladas). Gerar a base de novo ao reiniciar leva cerca de 0,7 segundo.
- O carregamento do painel leva cerca de 0,65 segundo com essa base. Pode ficar lento se o painel for atualizado com frequência; otimizar se necessário.
- O banco de desenvolvimento não tem administrador ainda, então o painel só pode ser acessado depois de `definir_admin`.
- Não há registro de quem fez cada ação no painel.
- Os testes automatizados cobrem só o acesso. Faltam testes de persistência e dos fluxos de participação.

## Orientações de manutenção
- Marcar como concluído somente após verificar o comportamento.
- Registrar links para commits, pull requests ou testes quando possível.
- Não inserir senhas, tokens ou chaves de API.
