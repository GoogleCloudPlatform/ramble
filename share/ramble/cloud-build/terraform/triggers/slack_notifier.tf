data "google_project" "project" {}

data "google_secret_manager_secret_version" "slack_webhook" {
  secret  = "ramble-slack-webhook"
  version = "latest"
}

resource "google_pubsub_topic" "cloud_builds" {
  name = "cloud-builds"
}

resource "google_service_account" "slack_notifier" {
  account_id   = "cloud-build-slack-notifier"
  display_name = "Cloud Build Slack Notifier Service Account"
}

resource "google_service_account_iam_member" "pubsub_token_creator" {
  service_account_id = google_service_account.slack_notifier.name
  role               = "roles/iam.serviceAccountTokenCreator"
  member             = "serviceAccount:service-${data.google_project.project.number}@gcp-sa-pubsub.iam.gserviceaccount.com"
}

resource "google_secret_manager_secret_iam_member" "slack_notifier_secret_access" {
  secret_id = data.google_secret_manager_secret_version.slack_webhook.secret
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.slack_notifier.email}"
}

resource "google_storage_bucket" "cloud_build_notifiers" {
  name                        = "${var.project_id}-cloud-build-notifiers"
  location                    = var.region
  uniform_bucket_level_access = true
}

resource "google_storage_bucket_iam_member" "slack_notifier_bucket_viewer" {
  bucket = google_storage_bucket.cloud_build_notifiers.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.slack_notifier.email}"
}

resource "google_storage_bucket_object" "slack_template" {
  name         = "slack.json"
  bucket       = google_storage_bucket.cloud_build_notifiers.name
  content_type = "application/json"
  content = jsonencode([
    {
      type = "section"
      text = {
        type = "mrkdwn"
        text = ":x: *Cloud Build Failure: ${google_cloudbuild_trigger.codecov_push.name}*\n*Status:* `{{.Build.Status}}`\n*Branch:* `{{.Params.branchName}}`\n*Commit:* `{{.Params.commitSha}}`\n*Build ID:* `{{.Build.Id}}`"
      }
    },
    {
      type = "divider"
    },
    {
      type = "actions"
      elements = [
        {
          type = "button"
          text = {
            type  = "plain_text"
            text  = "View Build Logs"
            emoji = true
          }
          url = "{{.Build.LogUrl}}"
        }
      ]
    }
  ])
}

resource "google_storage_bucket_object" "slack_config" {
  name         = "codecov-slack.yaml"
  bucket       = google_storage_bucket.cloud_build_notifiers.name
  content_type = "application/x-yaml"
  content      = <<-EOT
    apiVersion: cloud-build-notifiers/v1
    kind: SlackNotifier
    metadata:
      name: codecov-push-slack-notifier
    spec:
      notification:
        filter: >-
          build.build_trigger_id == "${google_cloudbuild_trigger.codecov_push.trigger_id}" &&
          build.status in [Build.Status.FAILURE, Build.Status.INTERNAL_ERROR, Build.Status.TIMEOUT, Build.Status.EXPIRED]
        params:
          branchName: $(build.substitutions['BRANCH_NAME'])
          commitSha: $(build.substitutions['COMMIT_SHA'])
        delivery:
          webhookUrl:
            secretRef: slack-webhook
        template:
          type: golang
          uri: gs://${google_storage_bucket.cloud_build_notifiers.name}/${google_storage_bucket_object.slack_template.name}
      secrets:
        - name: slack-webhook
          value: ${data.google_secret_manager_secret_version.slack_webhook.name}
  EOT
}

resource "google_cloud_run_v2_service" "slack_notifier" {
  name     = "cloud-build-slack-notifier"
  location = var.region

  template {
    service_account = google_service_account.slack_notifier.email

    containers {
      image = "us-east1-docker.pkg.dev/gcb-release/cloud-build-notifiers/slack:latest"

      env {
        name  = "CONFIG_PATH"
        value = "gs://${google_storage_bucket.cloud_build_notifiers.name}/${google_storage_bucket_object.slack_config.name}"
      }
      env {
        name  = "PROJECT_ID"
        value = var.project_id
      }
      env {
        name  = "CONFIG_HASH"
        value = sha256("${google_storage_bucket_object.slack_config.content}${google_storage_bucket_object.slack_template.content}")
      }
    }
  }

  depends_on = [
    google_secret_manager_secret_iam_member.slack_notifier_secret_access,
    google_storage_bucket_iam_member.slack_notifier_bucket_viewer,
  ]
}

resource "google_cloud_run_v2_service_iam_member" "slack_notifier_invoker" {
  name     = google_cloud_run_v2_service.slack_notifier.name
  location = google_cloud_run_v2_service.slack_notifier.location
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.slack_notifier.email}"
}

resource "google_pubsub_subscription" "slack_notifier" {
  name  = "cloud-build-slack-notifier-sub"
  topic = google_pubsub_topic.cloud_builds.name

  filter = "attributes.status = \"FAILURE\" OR attributes.status = \"INTERNAL_ERROR\" OR attributes.status = \"TIMEOUT\" OR attributes.status = \"EXPIRED\""

  push_config {
    push_endpoint = google_cloud_run_v2_service.slack_notifier.uri
    oidc_token {
      service_account_email = google_service_account.slack_notifier.email
    }
  }

  expiration_policy {
    ttl = ""
  }
}
