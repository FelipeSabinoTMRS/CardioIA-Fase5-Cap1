# Frente 3 — Interface, repositório e vídeo

**Disciplina de referência:** prototipação visual e boas práticas de projeto  
**Peso na nota base:** 2 pontos (interface funcional) + organização do repositório + vídeo

## Objetivo

Criar uma interface simples para o paciente conversar com o assistente, manter o GitHub organizado e gravar o vídeo de até 3 minutos.

O enunciado aceita HTML ou uma aplicação básica em React Native. O caminho mais direto para a nota é HTML + CSS + JavaScript consumindo o Flask da Frente 2.

## O que fazer

1. Tela de chat: o usuário envia mensagem e vê a resposta do assistente.
2. Integrar com `POST /api/chat` do backend. Sem mock na entrega final.
3. Deixar claro na interface que se trata de simulação acadêmica.
4. Organizar o repositório (README, pastas, `.gitignore`) junto com o restante do grupo.
5. Gravar vídeo de até 3 minutos com um fluxo real: saudação, sintoma, urgência e fallback.
6. Escrever o roteiro em `docs/roteiro_video.md` e colocar o link do vídeo no README principal.

## Organização sugerida

```text
frente-3-frontend/
|-- README.md
|-- index.html
|-- styles.css
`-- app.js
```

Se a equipe escolher React Native, documente aqui como subir o app e aponte o backend local.

## Contrato com as outras frentes

- Frente 2 precisa estar no ar para a interface e o vídeo.
- Frente 1 define o texto que aparece na tela.
- Frentes 4 e 5 podem ganhar uma tela extra depois (colar laudo ou ver alerta). Isso é opcional e não bloqueia a Parte 2.

## Entregáveis

- Interface funcional integrada ao backend.
- Repositório organizado (esta frente ajuda a fechar README, evidências e link do vídeo).
- Vídeo curto (até 3 minutos) demonstrando a interação.

## Fora desta frente

Skill do Watson, cliente da API IBM e os notebooks/robôs dos Ir Além.

## Como rodar (preencher quando o código existir)

```bash
# 1. subir o backend da Frente 2
# 2. abrir index.html pelo servidor local combinado com o grupo
```
