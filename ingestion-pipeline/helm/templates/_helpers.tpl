{{/*
Expand the name of the chart.
*/}}
{{- define "ingestion-pipeline.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "ingestion-pipeline.fullname" -}}
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
{{- define "ingestion-pipeline.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "ingestion-pipeline.labels" -}}
pipelines.kubeflow.org/v2_component: 'true'
helm.sh/chart: {{ include "ingestion-pipeline.chart" . }}
{{ include "ingestion-pipeline.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "ingestion-pipeline.selectorLabels" -}}
app.kubernetes.io/name: {{ include "ingestion-pipeline.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "ingestion-pipeline.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "ingestion-pipeline.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Pipeline-specific labels for a given pipeline
*/}}
{{- define "ingestion-pipeline.pipelineLabels" -}}
{{ include "ingestion-pipeline.labels" .root }}
ingestion-pipeline.ai/pipeline-name: {{ .pipelineName }}
ingestion-pipeline.ai/pipeline-source: {{ .pipelineConfig.source }}
{{- end }}

{{/*
Generate pipeline job name from key
*/}}
{{- define "ingestion-pipeline.pipelineJobName" -}}
{{- printf "add-%s-pipeline" .pipelineKey | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Filter enabled pipelines - returns JSON
*/}}
{{- define "ingestion-pipeline.enabledPipelines" -}}
{{- $enabledPipelines := dict -}}
{{- range $key, $pipeline := .Values.pipelines -}}
  {{- if $pipeline.enabled -}}
    {{- $_ := set $enabledPipelines $key $pipeline -}}
  {{- end -}}
{{- end -}}
{{- $enabledPipelines | toJson -}}
{{- end }}

{{/*
Prepare pipeline data for API call
*/}}
{{- define "ingestion-pipeline.preparePipelineData" -}}
{{- $pipeline := .pipelineConfig -}}
{{- $source := $pipeline.source -}}
{{- $sourceData := index $pipeline $source -}}
{{- $base := dict
    "name" $pipeline.name
    "version" $pipeline.version
    "source" $pipeline.source
    "embedding_model" $pipeline.embedding_model
    "vector_store_name" $pipeline.vector_store_name
-}}
{{- merge $base $sourceData | toJson -}}
{{- end }}
