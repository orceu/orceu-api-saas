# orceu-api-saas

`orceu-api-saas` é a API privada do SaaS Orceu, acessada exclusivamente pela aplicação web da organização (usuário autenticado via Supabase Auth).

Esta API é desenvolvida com **FastAPI**, utiliza o **JWT emitido pelo Supabase Auth** para autenticação e expõe os casos de uso definidos no `orceu-core`.

---

## 📦 Stack Técnica

- Python 3.11+
- [FastAPI](https://fastapi.tiangolo.com/)
- Supabase Auth (JWT validation)
- [Pydantic](https://docs.pydantic.dev/)
- Reutilização do pacote [`orceu-core`](https://github.com/orceu/orceu-core)
- Clean Architecture

---

## 🧱 Estrutura de Diretórios

```bash
orceu-api-saas/
│
├── main.py                          # Entrypoint da aplicação FastAPI
├── interface/
│   ├── plans/
│   │   ├── plan_controller.py       # Endpoints REST
│   │   ├── plan_request.py          # DTOs de entrada
│   │   └── plan_response.py         # DTOs de saída
│
├── infrastructure/
│   ├── auth/                        # Middleware de validação Supabase JWT
│   ├── database/                    # Adapters do Supabase
│   └── services/                    # Serviços auxiliares
│
├── tests/
│   ├── interface/
│   └── integration/
│
├── requirements.txt
├── .env.example
└── README.md
```

---

## 🚀 Execução local

1. Crie e ative o ambiente virtual:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Instale as dependências:

Se estiver usando Poetry:
```bash
poetry install
```
Ou, se estiver usando pip:
```bash
pip install -r requirements.txt
```

3. Execute a aplicação FastAPI com Uvicorn:

```bash
poetry run uvicorn app.main:app --reload
```

4. Acesse a documentação interativa:

Abra o navegador em [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 🔐 Autenticação

Esta API espera um token JWT válido do Supabase:

```http
Authorization: Bearer <TOKEN_DO_SUPABASE>
```

Tokens inválidos ou ausentes resultam em HTTP 401.

---

## 🧩 Exemplo de Controller (FastAPI)

```python
# interface/plans/plan_controller.py

from fastapi import APIRouter, Depends
from orceu.domain.plans import Plan
from orceu.application.plans.create_plan import CreatePlan
from interface.plans.plan_request import PlanRequest
from interface.auth import get_current_user

router = APIRouter(prefix="/plans", tags=["Plans"])

@router.post("/")
def create_plan(request: PlanRequest, user=Depends(get_current_user)):
    usecase = CreatePlan()
    plan = usecase.execute(user_id=user.id, **request.dict())
    return {"id": plan.id, "name": plan.name}
```

---

## 📚 Como usar o orceu-core

```python
from orceu.domain.plans import Plan
from orceu.application.plans.create_plan import CreatePlan

plan = Plan(id="...", name="Exemplo", ...)
usecase = CreatePlan()
result = usecase.execute(plan)
```

---

## ✅ Boas práticas para contribuidores

- Cada domínio deve ter seu próprio diretório em `interface/` (ex: `plans/`, `projects/`, `bases/`)
- Cada controller deve ser simples e delegar a lógica para o `orceu-core`
- Toda entrada/saída deve usar DTOs validados com `Pydantic`
- O middleware de autenticação deve ser isolado em `infrastructure/auth/`

---

## 🔁 Dependências

- [`orceu-core`](https://github.com/orceu/orceu-core)

---

## 📌 Licença

Uso exclusivo do ecossistema Orceu. Todos os direitos reservados.
