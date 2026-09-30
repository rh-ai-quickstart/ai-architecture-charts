{{/*
Expand the name of the chart.
*/}}
{{- define "object-storage.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "object-storage.fullname" -}}
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
{{- define "object-storage.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "object-storage.labels" -}}
helm.sh/chart: {{ include "object-storage.chart" . }}
{{ include "object-storage.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/component: storage
{{- with .Values.commonLabels }}
{{ toYaml . }}
{{- end }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "object-storage.selectorLabels" -}}
app.kubernetes.io/name: {{ include "object-storage.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app: {{ include "object-storage.fullname" . }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "object-storage.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "object-storage.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Create the name of the secret to use for S3 credentials
*/}}
{{- define "object-storage.secretName" -}}
{{- if .Values.s3.existingSecret }}
{{- .Values.s3.existingSecret }}
{{- else }}
{{- include "object-storage.fullname" . }}-credentials
{{- end }}
{{- end }}

{{/*
Create the name of the configmap
*/}}
{{- define "object-storage.configMapName" -}}
{{- include "object-storage.fullname" . }}-config
{{- end }}

{{/*
Create the name of the data PVC
*/}}
{{- define "object-storage.dataPvcName" -}}
{{- if .Values.storage.data.existingClaim }}
{{- .Values.storage.data.existingClaim }}
{{- else }}
{{- include "object-storage.fullname" . }}-data
{{- end }}
{{- end }}

{{/*
Create the name of the local storage PVC
*/}}
{{- define "object-storage.localStoragePvcName" -}}
{{- if .Values.storage.localStorage.existingClaim }}
{{- .Values.storage.localStorage.existingClaim }}
{{- else }}
{{- include "object-storage.fullname" . }}-local-storage
{{- end }}
{{- end }}

{{/*
Common annotations
*/}}
{{- define "object-storage.annotations" -}}
{{- with .Values.commonAnnotations }}
{{ toYaml . }}
{{- end }}
{{- end }}
