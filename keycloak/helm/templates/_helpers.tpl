{{/*
Expand the name of the chart.
*/}}
{{- define "keycloak.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "keycloak.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "keycloak.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "keycloak.labels" -}}
helm.sh/chart: {{ include "keycloak.chart" . }}
{{ include "keycloak.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- with .Values.commonLabels }}
{{ toYaml . }}
{{- end }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "keycloak.selectorLabels" -}}
app.kubernetes.io/name: {{ include "keycloak.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "keycloak.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "keycloak.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Keycloak instance name
*/}}
{{- define "keycloak.instanceName" -}}
{{- .Values.keycloak.name | default (include "keycloak.fullname" .) }}
{{- end }}

{{/*
Database secret name
*/}}
{{- define "keycloak.databaseSecretName" -}}
{{- if .Values.database.existingSecret.enabled }}
{{- .Values.database.existingSecret.name }}
{{- else }}
{{- printf "%s-db-secret" (include "keycloak.fullname" .) }}
{{- end }}
{{- end }}

{{/*
Database username key
*/}}
{{- define "keycloak.databaseUsernameKey" -}}
{{- if .Values.database.existingSecret.enabled }}
{{- .Values.database.existingSecret.usernameKey }}
{{- else }}
{{- "username" }}
{{- end }}
{{- end }}

{{/*
Database password key
*/}}
{{- define "keycloak.databasePasswordKey" -}}
{{- if .Values.database.existingSecret.enabled }}
{{- .Values.database.existingSecret.passwordKey }}
{{- else }}
{{- "password" }}
{{- end }}
{{- end }}

