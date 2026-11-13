# CPE Auto-Healing Dashboard

Dashboard HTML (ficheiro único, dark theme) que documenta as regras de auto-healing dos CPEs NOS, um modelo por manifesto:
Hitron Hub 5, Sagem FAST 5657, FAST 5670, FAST 3896-15, Strong GN630VE e Askey TCG310J.

## Correr

```powershell
python serve.py          # porta 13002 (0.0.0.0 → também 127.0.0.1 / localhost / IP da máquina)
python serve.py 13099    # outra porta
```

Abrir `http://localhost:13002` ou `http://<ip-do-servidor>:13002`. Só usa a biblioteca standard do Python.

## Regenerar o `index.html`

```powershell
python gen.py
```

- Lê os manifestos `.txt` (separador `€` ou `@`) da pasta `HEALINGS_DIR`
  (por omissão `OneDrive - NOS SGPS, S.A\NOS\healings`).
- Descrições do Hub 5 / FAST 5657 vêm de `base_models.json`; as dos restantes modelos estão no próprio `gen.py`.
- Só substitui os blocos de dados (`modelsMeta`, `database`, `manifestLines`); alterações à UI no `index.html` são preservadas.
- Falha se alguma linha do manifesto não tiver regra correspondente no dashboard.

## Ficheiros

| Ficheiro | Descrição |
|---|---|
| `index.html` | Dashboard |
| `serve.py` | Servidor HTTP (serve só o `index.html`) |
| `gen.py` | Gerador a partir dos manifestos |
| `base_models.json` | Metadados e descrições base do Hub 5 e FAST 5657 |
