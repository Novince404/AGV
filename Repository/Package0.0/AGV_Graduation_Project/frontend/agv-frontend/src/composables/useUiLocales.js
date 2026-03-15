import { computed } from 'vue'
import { LOCALE_TEXTS } from '../locales'

function fillTemplate(template, variables = {}) {
  return String(template ?? '').replace(/\{(\w+)\}/g, (_, key) => String(variables[key] ?? ''))
}

export function useUiLocales({ locale, t }) {
  const fallbackUi = LOCALE_TEXTS.en.uiLocales ?? {}

  const currentUi = computed(() => LOCALE_TEXTS[locale.value]?.uiLocales ?? fallbackUi)
  const pick = (key, fallback = {}) =>
    computed(() => currentUi.value?.[key] ?? fallbackUi?.[key] ?? fallback)

  const templateJsonLocale = pick('templateJson')
  const panelLocale = pick('panel')
  const panelSearchLocale = pick('panelSearch')
  const taskChainLocale = pick('taskChain')
  const taskBuilderLocale = pick('taskBuilder')
  const taskJsonLocale = pick('taskJson')
  const taskJsonExampleFileLocale = pick('taskJsonExampleFile')
  const queueViewLocale = pick('queueView')
  const experimentLocale = pick('experiment')
  const algorithmCompareLocale = pick('algorithmCompare')

  const toolbarGuideHintText = computed(
    () => currentUi.value?.toolbarGuideHintText ?? fallbackUi?.toolbarGuideHintText ?? ''
  )

  const guideCenterLocale = computed(() => {
    const base = currentUi.value?.guideCenter ?? fallbackUi?.guideCenter ?? {}
    return {
      ...base,
      workflowAuto: t('dispatch_help_auto'),
      workflowManual: t('dispatch_help_manual'),
      workflowForm: t('dispatch_help_form')
    }
  })

  const taskChainMapPickUiLocale = computed(() => {
    const base = currentUi.value?.taskChainMapPickUi ?? fallbackUi?.taskChainMapPickUi ?? {}
    return {
      start: base.start ?? 'Pick',
      cancel: base.cancel ?? 'Cancel',
      stageCount: base.stageCount ?? 'Plan',
      idle: (required, stages) =>
        fillTemplate(base.idleTemplate, {
          required,
          stages
        }),
      status: (picked, required, stages) =>
        picked >= required
          ? fillTemplate(base.statusDoneTemplate, {
              picked,
              required,
              stages
            })
          : fillTemplate(base.statusProgressTemplate, {
              picked,
              required,
              stages
            })
    }
  })

  return {
    templateJsonLocale,
    panelLocale,
    panelSearchLocale,
    guideCenterLocale,
    toolbarGuideHintText,
    taskChainLocale,
    taskBuilderLocale,
    taskJsonLocale,
    taskJsonExampleFileLocale,
    taskChainMapPickUiLocale,
    queueViewLocale,
    experimentLocale,
    algorithmCompareLocale
  }
}
