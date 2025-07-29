{{/*
Expand the name of the chart.
*/}}
{{- define "mcp-dbstore.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "mcp-dbstore.fullname" -}}
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
{{- define "mcp-dbstore.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "mcp-dbstore.labels" -}}
helm.sh/chart: {{ include "mcp-dbstore.chart" . }}
{{ include "mcp-dbstore.selectorLabels" . }}
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
{{- define "mcp-dbstore.selectorLabels" -}}
app.kubernetes.io/name: {{ include "mcp-dbstore.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "mcp-dbstore.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "mcp-dbstore.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Return the proper image name for MCP server
*/}}
{{- define "mcp-dbstore.mcpServer.image" -}}
{{- $registryName := .Values.mcpServer.image.registry -}}
{{- $repositoryName := .Values.mcpServer.image.repository -}}
{{- $tag := .Values.mcpServer.image.tag | toString -}}
{{- if .Values.global.imageRegistry }}
    {{- printf "%s/%s:%s" .Values.global.imageRegistry $repositoryName $tag -}}
{{- else -}}
    {{- printf "%s/%s:%s" $registryName $repositoryName $tag -}}
{{- end -}}
{{- end }}

{{/*
Return the proper image name for PostgreSQL
*/}}
{{- define "mcp-dbstore.postgresql.image" -}}
{{- $registryName := .Values.postgresql.image.registry -}}
{{- $repositoryName := .Values.postgresql.image.repository -}}
{{- $tag := .Values.postgresql.image.tag | toString -}}
{{- if .Values.global.imageRegistry }}
    {{- printf "%s/%s:%s" .Values.global.imageRegistry $repositoryName $tag -}}
{{- else -}}
    {{- printf "%s/%s:%s" $registryName $repositoryName $tag -}}
{{- end -}}
{{- end }}

{{/*
Return the proper storage class
*/}}
{{- define "mcp-dbstore.storageClass" -}}
{{- if .Values.global.storageClass -}}
    {{- .Values.global.storageClass -}}
{{- else -}}
    {{- .Values.postgresql.persistence.storageClass -}}
{{- end -}}
{{- end }} 