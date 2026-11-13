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

## Pendências prioritárias
- [ ] Validar o fluxo completo de ponta a ponta
- [ ] Implementar persistência com modelos Django e banco de dados
- [ ] Proteger operações administrativas com autenticação e autorização
- [ ] Criar testes automatizados dos fluxos principais
- [ ] Validar indicadores e integração com IA
- [ ] Revisar usabilidade e responsividade

## Próxima entrega sugerida
Épico: Descoberta e engajamento com eventos. Demonstrar cadastro de evento, visualização no feed, manifestação de interesse e atualização dos indicadores.

## Registro de atualizações
| Data | Alteração | Responsável | Evidência |
|---|---|---|---|
| AAAA-MM-DD | Descrever entrega ou alteração | Nome | PR, commit ou teste |

## Impedimentos e riscos
- Dados em memória podem ser perdidos ao reiniciar o servidor.
- Operações administrativas precisam de controle de acesso.

## Orientações de manutenção
- Marcar como concluído somente após verificar o comportamento.
- Registrar links para commits, pull requests ou testes quando possível.
- Não inserir senhas, tokens ou chaves de API.
