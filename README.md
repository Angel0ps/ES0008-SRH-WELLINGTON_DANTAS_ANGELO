# SISTEMA DE RESERVAS DE HOTEL POR WELLINGTON D. ANGELO
Projeto individial da disciplina ES0008 - Programação Orientada a Objetos ministrada no semestre 2026.2

---
## Objetivo
O projeto consiste em desenvolver uma API de um sistema de reservas de hotel. Este permitirá acesso aos dados de hóspedes, quartos e reservas com check-in/check-out. Também devendo conter tratamentos para política de cancelamento, tarifas por temporada, bloqueios por manutenção e relatórios de desempenho.

Além disto, buscarei aprender a utilizar as ferramentas FastAPI e SQlite para o desenvolvimento deste projeto.

---

## Como executar a API

A API utiliza a biblioteca padrão do Python e SQLite, sem precisar instalar um framework web.

Na raiz do repositório, execute:

```bash
# Iniciar o servidor na porta padrão 8000
python -m app.api

# Ou escolher outra porta
python -m app.api --porta 8080

# Opcional: definir o caminho do banco SQLite
python -m app.api --db srh_wda.db
```

Mantenha o terminal aberto enquanto utiliza a API. Para encerrar, pressione `Ctrl+C`.
O banco padrão é `srh_wda.db`, na raiz do projeto.

### Endpoints disponíveis

| Método | Endpoint | Finalidade |
|---|---|---|
| `GET` | `/quartos` | Listar quartos |
| `POST` | `/quartos` | Cadastrar quarto |
| `GET` | `/hospedes` | Listar hóspedes |
| `POST` | `/hospedes` | Cadastrar hóspede |
| `GET` | `/reservas` | Listar reservas |
| `GET` | `/reservas/{id}` | Consultar reserva |
| `POST` | `/reservas` | Criar reserva |
| `POST` | `/reservas/{id}/checkin` | Registrar check-in |
| `POST` | `/reservas/{id}/checkout` | Registrar check-out |
| `POST` | `/reservas/{id}/cancelar` | Cancelar reserva |
| `POST` | `/reservas/{id}/noshow` | Registrar não comparecimento |
| `POST` | `/reservas/{id}/pagamentos` | Lançar pagamento |
| `POST` | `/reservas/{id}/adicionais` | Lançar adicional |
| `GET` | `/relatorios/ocupacao?inicio=AAAA-MM-DD&fim=AAAA-MM-DD` | Consultar ocupação |

### Testar os endpoints

Os exemplos abaixo usam `curl` e assumem que o servidor está na porta `8000`.

```bash
# Cadastrar quarto
curl -i -X POST http://localhost:8000/quartos \
  -H 'Content-Type: application/json' \
  -d '{"numero":"101","capacidade":2,"diaria":100.0,"tipo":"Simples"}'

# Cadastrar hóspede
curl -i -X POST http://localhost:8000/hospedes \
  -H 'Content-Type: application/json' \
  -d '{"id":"h1","nome":"Ana Souza","documento":"12345678901","email":"ana@mail.com","telefone":"88999998888"}'

# Criar reserva
curl -i -X POST http://localhost:8000/reservas \
  -H 'Content-Type: application/json' \
  -d '{"id":"r1","quarto":"101","entrada":"2026-12-10","saida":"2026-12-12","hospedes_ids":["h1"],"qtd_hospedes":1}'

# Consultar reservas
curl -i http://localhost:8000/reservas

# Consultar relatório de ocupação
curl -i 'http://localhost:8000/relatorios/ocupacao?inicio=2026-12-01&fim=2026-12-31'
```

A API responde em JSON. Erros de validação das regras de negócio retornam `422`; campos obrigatórios ausentes ou parâmetros inválidos retornam `400`; recursos inexistentes retornam `404`.

### Executar os testes automatizados

Na raiz do projeto, com `pytest` instalado:

```bash
python -m pytest -q
```

Os testes usam banco SQLite em memória para não alterar os dados persistidos do projeto.

---

## Estrutura planejada de classes
```
app/
├── main.py
├── database.py
├── dependencies.py
├── models/
│   ├── __init__.py
│   ├── rastreios.py
│   ├── pessoas.py
│   ├── quartos.py
│   └── registros.py
├── schemas/
│   ├── hospede.py
│   ├── quarto.py
│   └── reserva.py
├── services/
│   ├── tarifas.py
│   └── relatorios.py
└── routes/
    ├── hospedes.py
    ├── quartos.py
    ├── reservas.py
    ├── bloqueios.py
    └── funcionarios.py
tests/
```
---
## UML Textual

```mermaid
classDiagram

%% Definição das Classes

   %% ==================== Super Classe Pessoas ===================

   class Pessoa <<abstrata>> {
      -str nome
      -str documento
      -str email
      -str telefone
      -str id
      +cadastrarPessoa() str
   }

   class Hospede <<concreta>> {
      +str observacoes
      +bool acessibilidade
      +gerenciarHospedes() str
      +requisitarHospede() str
  }

   class Funcionario <<concreta>> {
      -str cargo
      +gerenciarFuncionario() str
      +requisitarFuncionario() str
   }

   %% ======= Heranças ========

   Pessoa <|-- Hospede
   Pessoa <|-- Funcionario

   %% ====== Associações ======

   Hospede "0..*" -- "0..*" Reserva : Realiza
   Funcionario "1" --> "0..*" Bloqueio : Autoriza/Remove

   %% ================= Classe para Rastreabilidade ===============

      class Rastreabilidade <<abstrata>> {
      -date criado_em
      -date editado_em
      -str criado_por
      -str editado_por
      +rastrearCriacao() str
      +rastrearEdicao() str
   }

   %% =================== Super Classe Registro ===================
   
   class Registro <<abstrata>> {
      -str id
      -str quarto_relacionado
      -date data
      -char tipo
      -char status
      +novoRegistro() str
   }

   class Reserva <<concreta>> {
      -date data_entrada
      -date data_saida
      -int qtd_hospedes
      -float adicionais
      -list pagamentos
      +confirmar()
      +cancelarReserva() str
      +checkIn()
      +checkOut()
      +total_pago() float
      +total_devido() float
   }

   class Pagamento <<concreta>> {
      -char forma
      -str reserva
      -float valor
      +registrarPagamento() str
      +editarPagamento() str
      +statusPagamento() char
   }

   class Adicional <<concreta>> {
      -str descricao
      -float valor
      +registrarAdicional() str
      +editarAdicinoal() str
      +gerenciarDescricao() str
   }

   class Bloqueio <<concreta>> {
      -char tipo_de_bloqueio
      -str motivo
      -date prazo_para_desbloqueio
      +bloquearQuarto() str
      +editarBloqueio() str
      +agendarDesbloqueio() date
   }

   %% ====== Heranças ======

   Registro <|-- Reserva
   Registro <|-- Bloqueio

   %% == Herança Múltipla ==
   Rastreabilidade <|-- Reserva
   Rastreabilidade <|-- Pagamento
   Rastreabilidade <|-- Bloqueio

   %% ==== Composições ======

   Reserva "1" *-- "0..*" Pagamento : Composição
   Reserva "1" *-- "0..*" Adicional : Composição

   %% ====== Associações ======

   Registro "0..*" --> "1" Quarto : Associa-se com

   %% ================= Super Classe Quarto ===============

   class Quarto <<abstrata>> {
      -str numero
      -int capacidade
      -float diaria
      -char status
      -list bloqueios
      -str observacoes
      +requisitarQuarto() str
   }

   class Simples <<concreta>> {
      -str diferencial
      +diferenciarSimples() str
      +observacoesSimples() str
   }
   class Duplo <<concreta>> {
      -str diferencial
      +diferenciarDuplo() str
      +observacoesDuplo() str
   }
   class Luxo <<concreta>> {
      -str diferencial
      +diferenciarLuxo() str
      +observacoesLuxo() str
   }

   %% ======= Heranças =======

   Quarto <|-- Simples
   Quarto <|-- Duplo
   Quarto <|-- Luxo

   %% ======================= Serviços ====================

   class Tarifa <<concreta>> {
      -char tipo
      +calcularDiaria() float
      +aplicarDesconto() float
   }

   class Relatorio <<concreta>> {
      -char tipo
      +taxa_ocupacao() float
      +adr() float
      +revpar() float
   }

   %% ==== Relações ====

   Reserva ..> Tarifa : Usa
   Relatorio ..> Reserva : Lê
   ```
