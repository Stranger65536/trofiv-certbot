# Certbot certificate updater for Google Cloud Run

## Issue wildcard SSL certificates automatically for your domains managed by various DNS providers

## How it works

Google Cloud Run instance runs custom Docker image by schedule
every 3 months and stores up-to-date certificates in GCS bucket

## Supported DNS providers

<details>
<summary>See details</summary>

### GoDaddy (supported by `certbot-dns-godaddy` package)

<details>
<summary>See details</summary>

Use of this plugin requires a configuration file containing godaddy
API credentials, obtained from your
[API keys page](https://developer.godaddy.com/keys).

#### Example credentials file:

```ini
dns_godaddy_secret = 0123456789abcdef0123456789abcdef01234567
dns_godaddy_key = abcdef0123456789abcdef01234567abcdef0123
```

</details>

### Cloudflare (supported by `certbot-dns-cloudflare` package)

<details>
<summary>See details</summary>

Use of this plugin requires a configuration file containing
Cloudflare API credentials, obtained from your
[Cloudflare dashboard](https://dash.cloudflare.com/?to=/:account/profile/api-tokens)
.

Previously, Cloudflare’s “Global API Key” was used for authentication,
however this key can access the entire Cloudflare API for all domains
in your account, meaning it could cause a lot of damage if leaked.

Cloudflare’s newer API Tokens can be restricted to specific domains and
operations, and are therefore now the recommended authentication option.

The Token needed by Certbot requires Zone:DNS:Edit permissions for only
the zones you need certificates for.

#### Example credentials file using restricted API Token (recommended):

```ini
# Cloudflare API token used by Certbot
dns_cloudflare_api_token = 0123456789abcdef0123456789abcdef01234567
```

#### Example credentials file using Global API Key (not recommended):

```ini
# Cloudflare API credentials used by Certbot
dns_cloudflare_email = cloudflare@example.com
dns_cloudflare_api_key = 0123456789abcdef0123456789abcdef01234
```

</details>

### Google Cloud DNS (supported by `certbot-dns-google` package)

<details>
<summary>See details</summary>

Use of this plugin requires Google Cloud Platform API credentials for an
account with the following permissions:

- `dns.changes.create`
- `dns.changes.get`
- `dns.changes.list`
- `dns.managedZones.get`
- `dns.managedZones.list`
- `dns.resourceRecordSets.create`
- `dns.resourceRecordSets.delete`
- `dns.resourceRecordSets.list`
- `dns.resourceRecordSets.update`

Google provides
[instructions](https://developers.google.com/identity/protocols/OAuth2ServiceAccount#creatinganaccount)
for creating a service account and
[information about the required permissions](https://cloud.google.com/dns/access-control#permissions_and_roles)
.
If you’re running on Google Compute Engine / Google Cloud Build / Google
Cloud Run / etc.,
you
can [assign the service account to the instance](https://cloud.google.com/compute/docs/access/create-enable-service-accounts-for-instances)
which is running certbot updater. A credentials file is not required in
this case,
as they are automatically obtained by certbot through the metadata
service.

#### Example credentials file:

```json
{
  "type": "service_account",
  "project_id": "...",
  "private_key_id": "...",
  "private_key": "...",
  "client_email": "...",
  "client_id": "...",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://accounts.google.com/o/oauth2/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
   "client_x509_cert_url": "..."
}
```

Steps for GCP service account creation for Google Managed DNS Zone is
available on the [section below](#2-google-cloud-secret-creation)
</details>

### Amazon Route53 (supported by `certbot-dns-route53` package)

<details>
<summary>See details</summary>

Use of this plugin requires a configuration file containing
Amazon Web Services API credentials for an account
with the following permissions:

- `route53:ListHostedZones`
- `route53:GetChange`
- `route53:ChangeResourceRecordSets`

These permissions can be captured in an AWS policy like the one below.
Amazon provides
[information about managing access](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/access-control-overview.html)
and
[information about the required permissions](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/r53-api-permissions-ref.html)

#### Example AWS policy file:

```json
{
  "Version": "2012-10-17",
  "Id": "certbot-dns-route53 sample policy",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "route53:ListHostedZones",
        "route53:GetChange"
      ],
            "Resource": [
                "*"
            ]
        },
        {
            "Effect" : "Allow",
            "Action" : [
                "route53:ChangeResourceRecordSets"
            ],
            "Resource" : [
                "arn:aws:route53:::hostedzone/YOURHOSTEDZONEID"
            ]
        }
    ]
}
```

#### Example credentials config file:

```ini
[default]
aws_access_key_id = AKIAIOSFODNN7EXAMPLE
aws_secret_access_key = wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
```

</details>

### CloudXNS (supported by `certbot-dns-cloudxns` package)

<details>
<summary>See details</summary>

Use of this plugin requires a configuration file containing
CloudXNS API credentials, obtained from your CloudXNS
[API page](https://www.cloudxns.net/en/AccountManage/apimanage.html).

#### Example credentials file:

```ini
# CloudXNS API credentials used by Certbot
dns_cloudxns_api_key = 1234567890abcdef1234567890abcdef
dns_cloudxns_secret_key = 1122334455667788
```

</details>

### DigitalOcean (supported by `certbot-dns-digitalocean` package)

<details>
<summary>See details</summary>

Use of this plugin requires a configuration file containing
DigitalOcean API credentials, obtained from your DigitalOcean account’s
[Applications & API Tokens page](https://cloud.digitalocean.com/settings/api/tokens)
.

#### Example credentials file:

```ini
# DigitalOcean API credentials used by Certbot
dns_digitalocean_token = 0000111122223333444455556666777788889999aaaabbbbccccddddeeeeffff
```

</details>

### DNSimple (supported by `certbot-dns-dnsimple` package)

<details>
<summary>See details</summary>

Use of this plugin requires a configuration file containing
DNSimple API credentials, obtained from your DNSimple
[account page](https://dnsimple.com/user).

#### Example credentials file:

```ini
# DNSimple API credentials used by Certbot
dns_dnsimple_token = MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAw
```

</details>

### DNS Made Easy (supported by `certbot-dns-dnsmadeeasy` package)

<details>
<summary>See details</summary>

Use of this plugin requires a configuration file containing
DNS Made Easy API credentials, obtained from your DNS Made Easy
[account page](https://cp.dnsmadeeasy.com/account/info).

#### Example credentials file:

```ini
# DNS Made Easy API credentials used by Certbot
dns_dnsmadeeasy_api_key = 1c1a3c91-4770-4ce7-96f4-54c0eb0e457a
dns_dnsmadeeasy_secret_key = c9b5625f-9834-4ff8-baba-4ed5f32cae55
```

</details>

### Gehirn DNS (supported by `certbot-dns-gehirn` package)

<details>
<summary>See details</summary>

Use of this plugin requires a configuration file containing
Gehirn Infrastructure Service DNS API credentials, obtained from your
Gehirn Infrastructure Service [dashboard](https://gis.gehirn.jp/).

#### Example credentials file:

```ini
# Gehirn Infrastructure Service API credentials used by Certbot
dns_gehirn_api_token = 00000000-0000-0000-0000-000000000000
dns_gehirn_api_secret = MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAw
```

</details>

### Linode (supported by `certbot-dns-linode` package)

<details>
<summary>See details</summary>

Use of this plugin requires a configuration file containing Linode API
credentials, obtained from your Linode account’s
[Applications & API Tokens page (legacy)](https://manager.linode.com/profile/api)
or
[Applications & API Tokens page (new)](https://cloud.linode.com/profile/tokens)
.

#### Example credentials file:

```ini
# Linode API credentials used by Certbot
dns_linode_key = 0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ64
dns_linode_version = [<blank>|3|4]
```

</details>

### LuaDNS (supported by `certbot-dns-luadns` package)

<details>
<summary>See details</summary>

Use of this plugin requires a configuration file containing LuaDNS API
credentials,
obtained from
your [LuaDNS account settings page](https://api.luadns.com/settings).

#### Example credentials file:

```ini
# LuaDNS API credentials used by Certbot
dns_luadns_email = user@example.com
dns_luadns_token = 0123456789abcdef0123456789abcdef
```

</details>

### NS1 (supported by `certbot-dns-nsone` package)

<details>
<summary>See details</summary>

Use of this plugin requires a configuration file containing
NS1 API credentials, obtained from your
[NS1 account page](https://my.nsone.net/#/account/settings).

#### Example credentials file:

```ini
# NS1 API credentials used by Certbot
dns_nsone_api_key = MDAwMDAwMDAwMDAwMDAw
```

</details>

### OVH (supported by `certbot-dns-ovh` package)

<details>
<summary>See details</summary>

Use of this plugin requires a configuration file containing
OVH API credentials for an account with the following access rules:

- `GET /domain/zone/*`
- `PUT /domain/zone/*`
- `POST /domain/zone/*`
- `DELETE /domain/zone/*`

These credentials can be obtained there:

- [OVH Europe](https://eu.api.ovh.com/createToken/) (endpoint: ovh-eu)
- [OVH North America](https://ca.api.ovh.com/createToken/) (endpoint:
  ovh-ca)

#### Example credentials file:

```ini
# OVH API credentials used by Certbot
dns_ovh_endpoint = ovh-eu
dns_ovh_application_key = MDAwMDAwMDAwMDAw
dns_ovh_application_secret = MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAw
dns_ovh_consumer_key = MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAw
```

</details>

### Sakura Cloud (supported by `certbot-dns-sakuracloud` package)

<details>
<summary>See details</summary>

Use of this plugin requires a configuration file containing
Sakura Cloud DNS API credentials, obtained from your Sakura Cloud DNS
[api key page](https://secure.sakura.ad.jp/cloud/#!/apikey/top/).

#### Example credentials file:

```ini
# Sakura Cloud API credentials used by Certbot
dns_sakuracloud_api_token = 00000000-0000-0000-0000-000000000000
dns_sakuracloud_api_secret = MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAw
```

</details>

### Generic RFC-2136 DNS (supported by `certbot-dns-rfc2136` package)

<details>
<summary>See details</summary>

Use of this plugin requires a configuration file containing the
target DNS server and optional port that supports RFC 2136
Dynamic Updates, the name of the TSIG key, the TSIG key secret itself
and the algorithm used if it’s different to HMAC-MD5.

#### Example credentials file:

```ini
# Target DNS server (IPv4 or IPv6 address, not a hostname)
dns_rfc2136_server = 192.0.2.1
# Target DNS port
dns_rfc2136_port = 53
# TSIG key name
dns_rfc2136_name = keyname.
# TSIG key secret
dns_rfc2136_secret = 4q4wM/2I180UXoMyN4INVhJNi8V9BCV+jMw2mXgZw/CSuxUT8C7NKKFs AmKd7ak51vWKgSl12ib86oQRPkpDjg==
# TSIG key algorithm
dns_rfc2136_algorithm = HMAC-SHA512
```

</details>

</details>

## Secrets contract

Credentials (API tokens, etc.) for various providers have to be stored
at [Google Secrets Manager](https://cloud.google.com/secret-manager)
for secure access from Google Cloud Run instances.

## Installation

### NOPE disclaimer

> **Below step-by-step instruction is generally suitable for any
> DNS provider, but some steps are related only to
> Google Cloud DNS Managed Zone. These steps are fully optional if
> you're going to set up a job for a different DNS provider. These
> steps are marked as `NOPE` (Nether mind, Optional Paragraph Entity)**

### Required environment variables

The following list of environment variables is used across the
following steps. It's better to set them up in advance to don't face
issues related to unresolved variables in various commands.

- `GCP_PROJECT_ID` ex. `my-gcp-project`
- `GCP_CERTS_BUCKET` ex. `gs://my-ssl-certificates`
- `GCP_CERTS_BUCKET_PATH` ex. `domain/wildcard/`
- `GCP_SECRET_ID` ex. `certbot-updater-dns-provider-secret`
- `GCP_SECRET_DATA_FILE` ex. `/home/user/dns-provider-secret.json`,
  see supported providers section for file content details
- `GCP_SVC_ACC_NAME` ex. `certbot-updater`
- `GCP_ROLE_NAME`
  ex. `certbotAcmeDnsUpdater` **([NOPE](#nope-disclaimer))**
- `GCP_INVOKER_SVC_ACC_NAME` ex `certbot-updater-invoker`
- `GCP_SERVICE_NAME` ex. `certbot-updater`
- `DOMAINS` ex. `["*.example.com"]`
- `EMAIL` ex. `email@example.com` for Letsencrypt account
- `SCHEDULER_NAME` ex. `certbot-updater-mydomain`
- `GCP_REGION` ex `us-central1`

In sake of double-checking purposes, exporting commands of the
required variables are present before corresponding commands below.

### 1. GSC bucket creation (skip if you have it created)

```bash
> export GCP_PROJECT_ID="PROJECT_NAME" 
  export GCP_CERTS_BUCKET="gs://BUCKET_NAME"
```

> -b "off" enables fine-grained access control
> <br/> -c specifies standard storage class (highest availability)
> <br/>--pap enforced enables public access restriction

```bash
> gsutil mb \
  -p "${GCP_PROJECT_ID}" \
  -b "off" \
  -c "STANDARD" \
  --pap "enforced" \
  -l "US" \
  "${GCP_CERTS_BUCKET}"
```

### 2. Google Cloud Secret creation

The secret contains token / authentication for you DNS provider

```bash
> export GCP_SECRET_ID="certbot-updater-gcp-service-account"
  export GCP_SECRET_DATA_FILE="/home/user/certbot-updater.json" # this can be any text file
```

```bash
> gcloud secrets create "${GCP_SECRET_ID}" --replication-policy="automatic"
  gcloud secrets versions add "${GCP_SECRET_ID}" --data-file="${GCP_SECRET_DATA_FILE}"
```

> If you're going to use the job for various providers or with various
> credentials, consider repeating the step with different
> secret IDs and secrets data files

### 3. Service account creation & permissions grant

Modify the values accordingly to your project setup

```bash
> export GCP_PROJECT_ID="PROJECT_NAME"
  export GCP_CERTS_BUCKET="gs://BUCKET_NAME"
  export GCP_SVC_ACC_NAME="certbot-updater"
```

#### 4.1 **([NOPE](#nope-disclaimer))** Create a custom role to read & update DNS records

GCP doesn't provide fine-grained access over managed zones, so you can't
easily restrict
service account to have control over ACME challenge record on a specific
managed zone
(limited restriction may be gained by using project separation),
so creation of "uber role" is quite necessary

```bash
> export GCP_ROLE_NAME="certbotAcmeDnsUpdater"
```

```bash
> gcloud iam roles create "${GCP_ROLE_NAME}" --project="${GCP_PROJECT_ID}" \
  --title="${GCP_ROLE_NAME}" --description="Role for for automated SSL certificates renewal" \
  --permissions=dns.managedZones.get,dns.managedZones.list,dns.resourceRecordSets.list,dns.resourceRecordSets.delete,dns.resourceRecordSets.create,dns.resourceRecordSets.update,dns.changes.create,dns.changes.get,dns.changes.list \
  --stage=GA
```

#### 4.2 Create a service account to use with certbot

```bash
> gcloud iam service-accounts create "${GCP_SVC_ACC_NAME}" \
    --project="${GCP_PROJECT_ID}" \
    --description="SA for automated SSL certificates renewal & upload" \
    --display-name="${GCP_SVC_ACC_NAME}"
```

#### 4.3 **([NOPE](#nope-disclaimer))** Assign a custom DNS role to service account

```bash
> export GCP_ROLE_NAME="certbotAcmeDnsUpdater"
```

```bash
> gcloud projects add-iam-policy-binding ${GCP_PROJECT_ID} \
    --member=serviceAccount:${GCP_SVC_ACC_NAME}@${GCP_PROJECT_ID}.iam.gserviceaccount.com \
    --role=projects/${GCP_PROJECT_ID}/roles/${GCP_ROLE_NAME}
```

#### 4.4 Grant the service account write permission to GCS bucket

```bash
> gcloud storage buckets add-iam-policy-binding "${GCP_CERTS_BUCKET}" \
  --member="serviceAccount:${GCP_SVC_ACC_NAME}@${GCP_PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/storage.legacyBucketWriter"
```

#### 4.5 Grant the service account secret read permissions

```bash
> gcloud secrets add-iam-policy-binding "${GCP_SECRET_ID}" \
    --member="serviceAccount:${GCP_SVC_ACC_NAME}@${GCP_PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
```

> If you're going to use the job for various providers or with various
> credentials, consider repeating the step with different secret IDs

### 5. Clone public Docker image to Google Container (Artifact) Registry

Unfortunately, Google Cloud Run supports only running images from
Google Container Registry or Google Artifact Registry for Docker, so
the below steps are about pulling image from Docker Hub and pushing
it to Google Docker Registry in you project.

Setting up GCR or GCP Artifact Registry for docker is out of scope of
this manual and can be found on
[Google Official Documentation](https://cloud.google.com/container-registry/docs/quickstart)

#### 5.1 Push image to GCR (skip if you use GCP Artifact Registry)

```bash
> export GCP_PROJECT_ID="PROJECT_NAME"
  export IMAGE_TAG="docker.io/trofiv/certbot-updater:latest"
  export GCP_IMAGE_TAG="gcr.io/${GCP_PROJECT_ID}/certbot-updater:latest"
```

```bash
> docker pull "${IMAGE_TAG}"
  docker tag "${IMAGE_TAG}" "${GCP_IMAGE_TAG}"
  docker push "${GCP_IMAGE_TAG}"
```

If push fails, check the
[Google Official Documentation](https://cloud.google.com/container-registry/docs/quickstart)
for correct setup

#### 5.2 Push image to GCP Artifact Registry repository for Docker (skip if you use GCR)

View list of repositories

```bash
> gcloud artifacts repositories list
```

Pick `REPOSITORY` and `LOCATION` from the corresponding row and
replace them in the variables values:

```bash
> export GCP_PROJECT_ID="PROJECT_NAME"
  export GCP_REPOSITORY="REPOSITORY"
  export GCP_LOCATION="LOCATION"
  export IMAGE_TAG="docker.io/trofiv/certbot-updater:latest"
  export GCP_IMAGE_TAG=${GCP_LOCATION}-docker.pkg.dev/${GCP_PROJECT_ID}/${GCP_REPOSITORY}/certbot-updater:latest 
```

```bash
> docker pull "${IMAGE_TAG}"
  docker tag "${IMAGE_TAG}" "${GCP_IMAGE_TAG}"
  docker push "${GCP_IMAGE_TAG}"
```

If push fails, check the
[Google Official Documentation](https://cloud.google.com/container-registry/docs/quickstart)
for correct setup

### 6. Deploy Google Cloud Run instance

```bash
> export GCP_PROJECT_ID="PROJECT_NAME"
  export GCP_SVC_ACC_NAME="certbot-updater"
  export GCP_SERVICE_NAME="certbot-updater"
  export GCP_REGION="us-central1"
```

Assume that `GCP_IMAGE_TAG` variable is exported from the step 5

```bash
> gcloud run deploy "${GCP_SERVICE_NAME}" \
    --project "${GCP_PROJECT_ID}" \
    --platform "managed" \
    --service-account "${GCP_SVC_ACC_NAME}@${GCP_PROJECT_ID}.iam.gserviceaccount.com" \
    --image "${GCP_IMAGE_TAG}" \
    --region "${GCP_REGION}" \
    --concurrency 10 \
    --cpu 1 \
    --memory "256M" \
    --min-instances 0 \
    --max-instances 1 \
    --port 8080 \
    --timeout "3600s" \
    --ingress "all" \
    --no-allow-unauthenticated
```

### 7. Create a service account with permission to invoke the Cloud Run service:

```bash
> export GCP_PROJECT_ID="PROJECT_NAME"
  export GCP_INVOKER_SVC_ACC_NAME="certbot-updater-invoker"
  export GCP_SERVICE_NAME="certbot-updater"
```

#### 7.1 Create invoker service account

```bash
> gcloud iam service-accounts create "${GCP_INVOKER_SVC_ACC_NAME}" \
    --project="${GCP_PROJECT_ID}" \
    --description="SA for invoking certbot-updater service" \
    --display-name="${GCP_INVOKER_SVC_ACC_NAME}"
```

#### 7.2 Grant the service account permissions to invoke the Google Cloud Run service

```bash
> gcloud run services add-iam-policy-binding "${GCP_SERVICE_NAME}" \
    --project "${GCP_PROJECT_ID}" \
    --platform "managed" \
    --region "${GCP_REGION}" \
    --member "serviceAccount:${GCP_INVOKER_SVC_ACC_NAME}@${GCP_PROJECT_ID}.iam.gserviceaccount.com" \
    --role "roles/run.invoker"
```

### 8. Create a Cloud Scheduler HTTP job to invoke the certbot updater

> Consider configuring multiple schedulers or re-configuring
> the created one(s) to cover multiple domain names

```bash
> export GCP_PROJECT_ID="PROJECT_NAME"
  export GCP_INVOKER_SVC_ACC_NAME="certbot-updater-invoker"
  export GCP_SERVICE_NAME="certbot-updater"
  export GCP_SECRET_ID="certbot-updater-gcp-service-account"
  export DOMAINS="[\"*.example.com\"]"
  export GCP_CERTS_BUCKET="gs://my-ssl-certificates"
  export GCP_CERTS_BUCKET_PATH="domain/wildcard/"
  export EMAIL="email@example.com"
  export SCHEDULER_NAME="certbot-updater-mydomain"
  export GCP_REGION="us-central1"
```

```bash
# Capture the URL of the Cloud Run service:
> export SERVICE_URL=$(gcloud run services describe "${GCP_SERVICE_NAME}" --project "${GCP_PROJECT_ID}" --platform "managed" --region "${GCP_REGION}" --format 'value(status.url)')
```

```bash
> export CERTBOT_BODY=$(cat << EOF
{
  "provider": "google",
  "secret_id": "${GCP_SECRET_ID}", 
  "project": "${GCP_PROJECT_ID}",
  "domains": ${DOMAINS},
  "email": "${EMAIL}",
  "target_bucket": "${GCP_CERTS_BUCKET/gs:\/\//}",
  "target_bucket_path": "${GCP_CERTS_BUCKET_PATH}",
  "propagation_seconds": 600
}
EOF
)
```

```bash
> gcloud scheduler jobs create http "${SCHEDULER_NAME}" \
    --project "${GCP_PROJECT_ID}" \
    --description "Issue SSL certificates with certbot updater" \
    --uri "${SERVICE_URL}/certs" \
    --http-method "post" \
    --max-retry-attempts 1 \
    --time-zone "Etc/UTC" \
    --location "${GCP_REGION}" \
    --attempt-deadline "30m" \
    --headers "Content-Type=application/json" \
    --oidc-service-account-email "${GCP_INVOKER_SVC_ACC_NAME}@${GCP_PROJECT_ID}.iam.gserviceaccount.com" \
    --schedule "0 0 1 */2 *" \
    --message-body "${CERTBOT_BODY}"
```

#### (Optional) Run the scheduler manually

```bash
> gcloud scheduler jobs run "${SCHEDULER_NAME}" \
    --project "${GCP_PROJECT_ID}" \
    --location "${GCP_REGION}"
```

## Payload & Parameters

| Parameter           | Type          | Description                                                                                                                        | Sample value                              |
|---------------------|---------------|------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------|
| provider            | string        | DNS provider name, see [supported DNS providers](#supported-dns-providers). Name is the last token (`cloudflare`, `rfc2136`, etc.) | `"google"`                                |
| secret_id           | string        | Google Cloud Secret Manager secret id with authentication info for DNS provider                                                    | `"dns-provider-secret"`                   |
| project             | string        | GCP project name to fetch secrets & upload secrets to GCS                                                                          | `"my-gcp-project"`                        |
| domains             | string[]      | List of domain to issue certificate to. Note: wildcard `*.example.com` certificate should be the only item in the list             | `["www.example.com", "test.example.com"]` |
| email               | string        | Email used with Letsencrypt account                                                                                                | `"email@example.com"`                     |
| target_bucket       | string        | Bucket name without `gs://` prefix to upload certtificates to                                                                      | `"my-ssl-certificates-bucket"`            |
| target_bucket_path  | string        | Path within bucket to upload certificates to.                                                                                      | `"domain/wildcard/"`                      |
| propagation_seconds | Optional[int] | Number of seconds to wait until ACME record is propagated. Default is 60.                                                          | `600`                                     |