export const COMFY_WORKFLOW_PRESET_DEFAULT = 'preview'
export const COMFY_PROMPT_STYLE_DEFAULT = 'report'

export const COMFY_WORKFLOW_PRESETS = {
  preview: {
    width: 768,
    height: 576,
    steps: 14,
    cfg: 6.5,
    samplerName: 'euler',
    scheduler: 'normal'
  },
  showcase: {
    width: 896,
    height: 640,
    steps: 22,
    cfg: 7,
    samplerName: 'euler',
    scheduler: 'normal'
  },
  sdxl_showcase: {
    width: 960,
    height: 640,
    steps: 20,
    cfg: 6.5,
    samplerName: 'euler',
    scheduler: 'normal'
  }
}

export const COMFY_PROMPT_STYLES = {
  report: {
    promptFragments: [
      'presentation report style',
      'clear storytelling',
      'balanced labels and visuals',
      'designed for advisor or management review'
    ],
    negativeFragments: ['chaotic composition', 'overly artistic abstraction', 'visual confusion']
  },
  industrial_realistic: {
    promptFragments: [
      'industrial realistic rendering',
      'practical warehouse materials',
      'credible equipment proportions',
      'real logistics facility atmosphere'
    ],
    negativeFragments: ['cartoon rendering', 'toy-like machinery', 'plastic scene appearance']
  },
  infographic: {
    promptFragments: [
      'infographic-friendly composition',
      'clean information hierarchy',
      'diagram-like clarity',
      'easy to explain in slides'
    ],
    negativeFragments: ['messy typography', 'confusing overlays', 'unstructured composition']
  }
}

function normalizePresetKey(presetKey) {
  const normalized = String(presetKey || '').trim().toLowerCase()
  return Object.prototype.hasOwnProperty.call(COMFY_WORKFLOW_PRESETS, normalized)
    ? normalized
    : COMFY_WORKFLOW_PRESET_DEFAULT
}

function normalizeStyleKey(styleKey) {
  const normalized = String(styleKey || '').trim().toLowerCase()
  return Object.prototype.hasOwnProperty.call(COMFY_PROMPT_STYLES, normalized)
    ? normalized
    : COMFY_PROMPT_STYLE_DEFAULT
}

function sourceTypeLabelForFileName(sourceType) {
  return String(sourceType || 'custom_json')
    .trim()
    .replace(/[^a-zA-Z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '') || 'custom_json'
}

function sanitizeFileNameToken(value, fallback = '') {
  const normalized = String(value || '')
    .trim()
    .replace(/[^a-zA-Z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '')
  return normalized || fallback
}

function uniqueFragments(items) {
  return [...new Set(items.map(item => String(item || '').trim()).filter(Boolean))]
}

export function getComfyWorkflowPresetConfig(presetKey) {
  return COMFY_WORKFLOW_PRESETS[normalizePresetKey(presetKey)]
}

export function getComfyPromptStyleConfig(styleKey) {
  return COMFY_PROMPT_STYLES[normalizeStyleKey(styleKey)]
}

export function buildDefaultComfyPromptText({
  sourceType,
  sourceRef,
  presetKey = COMFY_WORKFLOW_PRESET_DEFAULT,
  styleKey = COMFY_PROMPT_STYLE_DEFAULT
}) {
  const normalizedPresetKey = normalizePresetKey(presetKey)
  const normalizedStyleKey = normalizeStyleKey(styleKey)
  const trimmedRef = String(sourceRef || '').trim()
  const sourceRefFragment = trimmedRef ? `source reference ${trimmedRef}` : ''
  const baseFragments = [
    'enterprise warehouse AGV dispatch visualization',
    'smart logistics control scene',
    'industrial environment',
    'clean lane boundaries',
    'clear blocked zones',
    'no people'
  ]

  const sourceFragments = {
    map_profile: [
      'warehouse layout focused composition',
      'route planning context',
      'readable floor zoning',
      'top-down or slight isometric logistics map view',
      'clear grid discipline and aisle readability',
      sourceRefFragment
    ],
    point_template_export: [
      'planning board style visualization',
      'reusable waypoint emphasis',
      'task template overview',
      'station markers and workflow handoff emphasis',
      'organized planning document feeling',
      sourceRefFragment
    ],
    experiment_records: [
      'algorithm comparison visual',
      'decision support infographic style',
      'route efficiency emphasis',
      'before and after route comparison layout',
      'presentation slide ready analytics aesthetic',
      sourceRefFragment
    ],
    map_profile_diff: [
      'before and after layout comparison',
      'operational change summary',
      'relocated AGV context',
      'change impact storytelling',
      'map revision presentation board',
      sourceRefFragment
    ],
    custom_json: [
      'smart logistics showcase visual',
      'data-driven enterprise render',
      'generic enterprise digital twin illustration',
      sourceRefFragment
    ]
  }

  const sourceStyleFragments = {
    map_profile: {
      report: ['advisor presentation board', 'clear map explanation priority'],
      industrial_realistic: ['credible warehouse floor texture', 'real operational facility mood'],
      infographic: ['layout legend friendly composition', 'diagram-ready zone separation']
    },
    point_template_export: {
      report: ['workflow summary board', 'step by step planning explanation'],
      industrial_realistic: ['real dispatch planning desk atmosphere', 'practical planning artifacts'],
      infographic: ['schematic waypoint presentation', 'process card readability']
    },
    experiment_records: {
      report: ['algorithm recommendation summary slide', 'decision meeting ready composition'],
      industrial_realistic: ['operations review dashboard feeling', 'applied logistics optimization context'],
      infographic: ['data story composition', 'clean metric-first visual hierarchy']
    },
    map_profile_diff: {
      report: ['before after review board', 'change approval meeting visual'],
      industrial_realistic: ['credible retrofit planning context', 'operational adjustment realism'],
      infographic: ['change impact infographic', 'clear relocation and trimming annotation space']
    },
    custom_json: {
      report: ['enterprise concept slide', 'business-ready communication visual'],
      industrial_realistic: ['real smart logistics scene', 'credible industrial digital twin mood'],
      infographic: ['structured information poster', 'clear explanatory composition']
    }
  }

  const presetFragments = {
    preview: [
      'top-down control room friendly angle',
      'fast preview quality',
      'simple clean lighting',
      'readable layout first'
    ],
    showcase: [
      'polished enterprise showcase',
      'premium industrial lighting',
      'slightly cinematic but realistic',
      'high clarity floor markings',
      'executive presentation quality'
    ],
    sdxl_showcase: [
      'sdxl-ready industrial showcase',
      'high fidelity warehouse materials',
      'clean presentation lighting',
      'balanced enterprise presentation framing',
      'premium enterprise hero visual',
      'high detail AGV body panels and floor texture'
    ]
  }

  const compositionFragments =
    normalizedPresetKey === 'preview'
      ? ['readable layout first', 'simple camera angle', 'minimal clutter']
      : normalizedPresetKey === 'sdxl_showcase'
        ? ['hero composition', 'clean depth and perspective', 'strong presentation hierarchy']
        : ['showcase composition', 'balanced cinematic perspective', 'presentation-ready scene']

  const fragments = uniqueFragments([
    ...baseFragments,
    ...(sourceFragments[String(sourceType || 'custom_json')] || sourceFragments.custom_json),
    ...(presetFragments[normalizedPresetKey] || presetFragments.preview),
    ...(COMFY_PROMPT_STYLES[normalizedStyleKey]?.promptFragments || COMFY_PROMPT_STYLES.report.promptFragments),
    ...(sourceStyleFragments[String(sourceType || 'custom_json')]?.[normalizedStyleKey] || []),
    ...compositionFragments
  ])

  return fragments.join(', ')
}

export function buildDefaultComfyNegativePromptText({
  sourceType,
  presetKey = COMFY_WORKFLOW_PRESET_DEFAULT,
  styleKey = COMFY_PROMPT_STYLE_DEFAULT
}) {
  const normalizedPresetKey = normalizePresetKey(presetKey)
  const normalizedStyleKey = normalizeStyleKey(styleKey)
  const baseFragments = [
    'low quality',
    'blurry',
    'duplicate AGV',
    'deformed vehicle',
    'crowded scene',
    'humans',
    'text watermark',
    'unreadable labels',
    'noisy background',
    'fantasy style',
    'anime style',
    'nsfw'
  ]

  const sourceFragments = {
    map_profile: ['messy zoning', 'broken aisle alignment', 'overdecorated warehouse'],
    point_template_export: ['chaotic icon layout', 'broken waypoint markers', 'document clutter'],
    experiment_records: ['fake chart labels', 'misleading infographic text', 'visual clutter'],
    map_profile_diff: ['unclear before after separation', 'ambiguous change zones'],
    custom_json: ['undefined subject', 'random unrelated machinery']
  }

  const sourceStyleFragments = {
    map_profile: {
      report: ['unclear presentation board'],
      industrial_realistic: ['fake concrete texture', 'unreal warehouse materials'],
      infographic: ['legend clutter', 'confusing zoning markers']
    },
    point_template_export: {
      report: ['unclear workflow ordering'],
      industrial_realistic: ['random office props'],
      infographic: ['marker overlap', 'bad diagram spacing']
    },
    experiment_records: {
      report: ['weak comparison emphasis'],
      industrial_realistic: ['random dramatic mood'],
      infographic: ['fake chart overload', 'busy analytical clutter']
    },
    map_profile_diff: {
      report: ['unclear revision story'],
      industrial_realistic: ['meaningless machinery clutter'],
      infographic: ['before after confusion']
    },
    custom_json: {
      report: ['generic corporate stock look'],
      industrial_realistic: ['unrelated industrial objects'],
      infographic: ['overloaded icon noise']
    }
  }

  const presetFragments = {
    preview: ['dramatic shadows', 'extreme perspective', 'heavy reflections', 'motion blur'],
    showcase: ['cartoon shading', 'toy-like vehicle', 'oversaturated colors', 'fisheye lens'],
    sdxl_showcase: [
      'overprocessed hdr',
      'plastic materials',
      'mangled perspective',
      'cropped AGV',
      'bad industrial texture',
      'chaotic lighting'
    ]
  }

  return uniqueFragments([
    ...baseFragments,
    ...(sourceFragments[String(sourceType || 'custom_json')] || sourceFragments.custom_json),
    ...(presetFragments[normalizedPresetKey] || presetFragments.preview),
    ...(COMFY_PROMPT_STYLES[normalizedStyleKey]?.negativeFragments || COMFY_PROMPT_STYLES.report.negativeFragments),
    ...(sourceStyleFragments[String(sourceType || 'custom_json')]?.[normalizedStyleKey] || [])
  ]).join(', ')
}

export function buildDefaultComfyWorkflowTemplate({
  checkpointName,
  promptText,
  sourceType,
  sourceRef,
  presetKey = COMFY_WORKFLOW_PRESET_DEFAULT,
  styleKey = COMFY_PROMPT_STYLE_DEFAULT
}) {
  const preset = getComfyWorkflowPresetConfig(presetKey)
  const normalizedPrompt =
    String(promptText || '').trim() ||
    'enterprise warehouse AGV dispatch visualization, professional industrial presentation, no people'
  const normalizedCheckpoint = String(checkpointName || '').trim()
  const negativePrompt = buildDefaultComfyNegativePromptText({
    sourceType,
    presetKey,
    styleKey
  })
  const sourceLabel = sourceTypeLabelForFileName(sourceType)
  const sourceRefToken = sanitizeFileNameToken(sourceRef, 'default')
  const presetLabel = normalizePresetKey(presetKey).toUpperCase()
  const styleLabel = normalizeStyleKey(styleKey).toUpperCase()

  return {
    '3': {
      inputs: {
        seed: 123456789,
        steps: preset.steps,
        cfg: preset.cfg,
        sampler_name: preset.samplerName,
        scheduler: preset.scheduler,
        denoise: 1,
        model: ['4', 0],
        positive: ['6', 0],
        negative: ['7', 0],
        latent_image: ['5', 0]
      },
      class_type: 'KSampler'
    },
    '4': {
      inputs: {
        ckpt_name: normalizedCheckpoint
      },
      class_type: 'CheckpointLoaderSimple'
    },
    '5': {
      inputs: {
        width: preset.width,
        height: preset.height,
        batch_size: 1
      },
      class_type: 'EmptyLatentImage'
    },
    '6': {
      inputs: {
        text: normalizedPrompt,
        clip: ['4', 1]
      },
      class_type: 'CLIPTextEncode'
    },
    '7': {
      inputs: {
        text: negativePrompt,
        clip: ['4', 1]
      },
      class_type: 'CLIPTextEncode'
    },
    '8': {
      inputs: {
        samples: ['3', 0],
        vae: ['4', 2]
      },
      class_type: 'VAEDecode'
    },
    '9': {
      inputs: {
        filename_prefix: `AGV_ComfyUI_${String(sourceLabel).toUpperCase()}_${String(sourceRefToken).toUpperCase()}_${presetLabel}_${styleLabel}`,
        images: ['8', 0]
      },
      class_type: 'SaveImage'
    }
  }
}
