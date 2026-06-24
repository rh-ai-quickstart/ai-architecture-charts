{{/*
Expand the name of the chart.
*/}}
{{- define "ogx-ai.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "ogx-ai.fullname" -}}
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
{{- define "ogx-ai.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "ogx-ai.labels" -}}
helm.sh/chart: {{ include "ogx-ai.chart" . }}
{{ include "ogx-ai.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "ogx-ai.selectorLabels" -}}
app.kubernetes.io/name: {{ include "ogx-ai.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "ogx-ai.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "ogx-ai.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{- define "ogx-ai.mergeModels" -}}
  {{- $root := . }}
  {{- $globalModels := .Values.global | default dict }}
  {{- $globalModels := $globalModels.models | default dict }}
  {{- $localModels := .Values.models | default dict }}
  {{- $merged := merge $globalModels $localModels }}
  {{- range $key, $model := $merged }}
    {{- if not $model.url }}
      {{- $url := printf "https://%s.%s.svc.cluster.local/v1" $key $root.Release.Namespace }}
      {{- if $root.Values.rawDeploymentMode }}
        {{- $url = printf "http://%s-vllm.%s.svc.cluster.local/v1" $key $root.Release.Namespace }}
      {{- end }}
      {{- $_ := set $merged $key (merge $model (dict "url" $url)) }}
    {{- end }}
  {{- end }}
  {{- toJson $merged }}
{{- end }}

{{- define "ogx-ai.mergeMcpServers" -}}
  {{- $globalServers := .Values.global | default dict }}
  {{- $globalServers := index $globalServers "mcp-servers" | default dict }}
  {{- $localServers := index .Values "mcp-servers" | default dict }}
  {{- $merged := merge $globalServers $localServers }}
  {{- toJson $merged }}
{{- end }}

{{- define "ogx-ai.hasEnabledModels" -}}
  {{- $found := false }}
  {{- $models := include "ogx-ai.mergeModels" . | fromJson }}
  {{- range $key, $model := $models }}
    {{- if and $model.enabled (ne $key "remote-llm") }}
      {{- $found = true }}
    {{- end }}
  {{- end }}
  {{- if $found }}true{{- end }}
{{- end }}
