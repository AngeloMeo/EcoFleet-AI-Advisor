# Guida Pratica: Configurazione e Uso della CI/CD (GitHub Actions)

Questa guida illustra come abilitare e utilizzare la pipeline CI/CD di **EcoFleet AI Advisor** per il deployment automatico del backend (**Azure Functions**) e del frontend (**Dashboard Web App**).

---

## 🏗️ Architettura CI/CD

I workflow sono definiti nella cartella [`.github/workflows/`](file:///c:/Users/Angelo/Desktop/Universita_Codice/CloudComputing/EcoFleet-AI-Advisor/.github/workflows):

| Workflow | File | Trigger | Target Azure |
|---|---|---|---|
| **Deploy Backend** | [`backend-deploy.yml`](file:///c:/Users/Angelo/Desktop/Universita_Codice/CloudComputing/EcoFleet-AI-Advisor/.github/workflows/backend-deploy.yml) | Modifiche a `api/**` | Azure Function App (`func-ecofleet`) |
| **Deploy Frontend** | [`frontend-deploy.yml`](file:///c:/Users/Angelo/Desktop/Universita_Codice/CloudComputing/EcoFleet-AI-Advisor/.github/workflows/frontend-deploy.yml) | Modifiche a `dashboard/**` | Azure Web App (`ecofleet`) |

Entrambi i workflow utilizzano la medesima azione ufficiale [`azure/login@v2`](https://github.com/Azure/login) alimentata da un singolo secret GitHub denominato `AZURE_CREDENTIALS`.

---

## 🚀 Procedura di Attivazione (One-Time Setup)

### Passo 1: Creazione del Service Principal su Azure

Apri la **Azure Cloud Shell** (o un terminale con Azure CLI autenticato) ed esegui:

```bash
# Sostituisci la subscription se diversa
SUBSCRIPTION_ID="ab4bd52a-d7fd-4e75-99b9-f0d369aca6da"
RESOURCE_GROUP="EcoFleetAdvisor"

az ad sp create-for-rbac \
  --name "github-ecofleet-deploy" \
  --role contributor \
  --scopes /subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP \
  --sdk-auth
```

> [!NOTE]
> Il parametro `--scopes` applica il principio di **Least Privilege**: il bot di GitHub avrà permessi solo ed esclusivamente all'interno del Resource Group del progetto, senza accedere ad altre risorse della tua subscription.

Il comando restituirà un blocco JSON formattato così:

```json
{
  "clientId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "clientSecret": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "subscriptionId": "ab4bd52a-d7fd-4e75-99b9-f0d369aca6da",
  "tenantId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "activeDirectoryEndpointUrl": "https://login.microsoftonline.com",
  "resourceManagerEndpointUrl": "https://management.azure.com/",
  "activeDirectoryGraphResourceId": "https://graph.windows.net/",
  "sqlManagementEndpointUrl": "https://management.core.windows.net:8443/",
  "galleryEndpointUrl": "https://gallery.azure.com/",
  "managementEndpointUrl": "https://management.core.windows.net/"
}
```

Copia **tutto il blocco JSON** (comprese le parentesi graffe `{ }`).

---

### Passo 2: Aggiunta del Secret su GitHub

1. Vai sul repository GitHub del progetto: [EcoFleet-AI-Advisor](https://github.com/AngeloMeo/EcoFleet-AI-Advisor).
2. Clicca su **Settings** (ingranaggio in alto a destra).
3. Nella barra laterale sinistra, vai su **Secrets and variables** ➔ **Actions**.
4. Clicca su **New repository secret**.
5. Compila i campi:
   - **Name**: `AZURE_CREDENTIALS`
   - **Secret**: Incolla il JSON copiato al Passo 1.
6. Clicca su **Add secret**.

**Fatto! La CI/CD è ora attiva e collegata al tuo cloud Azure.** 🎉

---

## 🔄 Come Utilizzare la CI/CD

### 1. Deployment Automatico (Consigliato)
Ogni volta che fai un commit e un push sul branch `main`:
- Se hai modificato file dentro [`api/`](file:///c:/Users/Angelo/Desktop/Universita_Codice/CloudComputing/EcoFleet-AI-Advisor/api), GitHub Actions prepara i pacchetti Python, crea il file zip e aggiorna la Function App.
- Se hai modificato file dentro [`dashboard/`](file:///c:/Users/Angelo/Desktop/Universita_Codice/CloudComputing/EcoFleet-AI-Advisor/dashboard), GitHub Actions aggiorna i file HTML/CSS/JS della Web App.

### 2. Deployment Manuale (On-Demand)
Se vuoi forzare un deploy senza fare modifiche al codice:
1. Su GitHub, vai nella scheda **Actions**.
2. Nel menu a sinistra seleziona il workflow desiderato (**Deploy Backend** o **Deploy Frontend**).
3. Clicca sul menu a tendina **Run workflow** (in alto a destra).
4. Conferma con **Run workflow**.

---

## 🛠️ Risoluzione dei Problemi Frequenti

| Problema | Causa | Soluzione |
|---|---|---|
| `Login failed with Error: ...` | Il secret `AZURE_CREDENTIALS` contiene caratteri mancanti o è scaduto | Rigenera il Service Principal con il comando del Passo 1 e aggiorna il secret su GitHub. |
| `ResourceNotFound: The Resource 'Microsoft.Web/sites/...' was not found` | Il nome dell'app nel workflow (`func-ecofleet` o `ecofleet`) non corrisponde al nome reale su Azure | Verifica che l'infrastruttura sia stata deployata con `use_random_suffix = false`, oppure allinea la variabile `AZURE_FUNCTIONAPP_NAME` / `AZURE_WEBAPP_NAME` nel workflow. |
| Errore `zip: command not found` | Runner personalizzato privo di utilità base | I workflow usano `ubuntu-latest` che ha `zip` preinstallato per default. |
