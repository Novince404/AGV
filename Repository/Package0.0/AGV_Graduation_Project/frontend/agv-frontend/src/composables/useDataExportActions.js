import { downloadCsvFile, downloadJsonFile } from '../utils/fileDownload'

export function useDataExportActions(options) {
  const {
    jsonText,
    jsonStatus,
    taskJsonLocale,
    taskJsonExampleFileLocale,
    buildTaskJsonExamplePayload,
    experimentRecords,
    experimentStatus,
    experimentStatusType,
    experimentLocale,
    panelSections,
    buildCompareSnapshot,
    experimentCsvRowsFromRecords,
    rowsToCsv
  } = options

  function setExperimentStatus(type, message) {
    experimentStatusType.value = type
    experimentStatus.value = message
  }

  function fillTaskJsonExample(mode) {
    jsonText.value = JSON.stringify(buildTaskJsonExamplePayload(mode), null, 2)
    jsonStatus.value = mode === 'chain' ? taskJsonLocale.value.chainLoaded : taskJsonLocale.value.singleLoaded
  }

  function downloadTaskJsonExample(mode) {
    const payloadText = JSON.stringify(buildTaskJsonExamplePayload(mode), null, 2)
    const fileName = mode === 'chain' ? 'agv-stage-task-example.json' : 'agv-single-task-example.json'

    downloadJsonFile(fileName, payloadText)
    jsonStatus.value =
      mode === 'chain'
        ? taskJsonExampleFileLocale.value.chainDownloaded
        : taskJsonExampleFileLocale.value.singleDownloaded
  }

  function saveCurrentExperimentRecord() {
    const snapshot = buildCompareSnapshot()
    if (!snapshot) {
      setExperimentStatus('error', experimentLocale.value.noCompare)
      return
    }

    experimentRecords.value = [snapshot, ...experimentRecords.value]
    setExperimentStatus('success', experimentLocale.value.savedOk)
    panelSections.value = {
      ...panelSections.value,
      experiments: true
    }
  }

  function exportCurrentCompareResultJson() {
    const snapshot = buildCompareSnapshot()
    if (!snapshot) {
      setExperimentStatus('error', experimentLocale.value.noCompare)
      return
    }

    downloadJsonFile(`agv-compare-${snapshot.id}.json`, JSON.stringify(snapshot, null, 2))
    setExperimentStatus('success', experimentLocale.value.exportCurrentJsonOk)
  }

  function exportCurrentCompareResultCsv() {
    const snapshot = buildCompareSnapshot()
    if (!snapshot) {
      setExperimentStatus('error', experimentLocale.value.noCompare)
      return
    }

    downloadCsvFile(`agv-compare-${snapshot.id}.csv`, rowsToCsv(experimentCsvRowsFromRecords([snapshot])))
    setExperimentStatus('success', experimentLocale.value.exportCurrentCsvOk)
  }

  function exportAllExperimentRecordsJson() {
    if (experimentRecords.value.length === 0) {
      setExperimentStatus('error', experimentLocale.value.exportEmpty)
      return
    }

    downloadJsonFile('agv-experiment-records.json', JSON.stringify(experimentRecords.value, null, 2))
    setExperimentStatus('success', experimentLocale.value.exportAllJsonOk)
  }

  function exportAllExperimentRecordsCsv() {
    if (experimentRecords.value.length === 0) {
      setExperimentStatus('error', experimentLocale.value.exportEmpty)
      return
    }

    downloadCsvFile('agv-experiment-records.csv', rowsToCsv(experimentCsvRowsFromRecords(experimentRecords.value)))
    setExperimentStatus('success', experimentLocale.value.exportAllCsvOk)
  }

  function exportExperimentRecord(record, format) {
    if (!record) return
    if (format === 'csv') {
      downloadCsvFile(`agv-experiment-${record.id}.csv`, rowsToCsv(experimentCsvRowsFromRecords([record])))
      return
    }

    downloadJsonFile(`agv-experiment-${record.id}.json`, JSON.stringify(record, null, 2))
  }

  function deleteExperimentRecord(recordId) {
    experimentRecords.value = experimentRecords.value.filter(record => record.id !== recordId)
    setExperimentStatus('info', experimentLocale.value.deletedOk)
  }

  function clearExperimentRecords() {
    experimentRecords.value = []
    setExperimentStatus('info', experimentLocale.value.clearedOk)
  }

  return {
    setExperimentStatus,
    fillTaskJsonExample,
    downloadTaskJsonExample,
    saveCurrentExperimentRecord,
    exportCurrentCompareResultJson,
    exportCurrentCompareResultCsv,
    exportAllExperimentRecordsJson,
    exportAllExperimentRecordsCsv,
    exportExperimentRecord,
    deleteExperimentRecord,
    clearExperimentRecords
  }
}
