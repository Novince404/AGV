export const DEFAULT_POINT_LIBRARY = [
  {
    id: 'inbound_a',
    x: 0,
    y: 1,
    nameKey: 'point_name_inbound_a',
    zoneKey: 'point_zone_inbound',
    aliases: ['dock', 'receiving', '入库', '搬入', '0,1']
  },
  {
    id: 'inbound_b',
    x: 0,
    y: 6,
    nameKey: 'point_name_inbound_b',
    zoneKey: 'point_zone_inbound',
    aliases: ['dock', 'receiving', '入库', '搬入', '0,6']
  },
  {
    id: 'outbound_a',
    x: 9,
    y: 1,
    nameKey: 'point_name_outbound_a',
    zoneKey: 'point_zone_outbound',
    aliases: ['shipping', 'delivery', '出库', '搬出', '9,1']
  },
  {
    id: 'outbound_b',
    x: 9,
    y: 6,
    nameKey: 'point_name_outbound_b',
    zoneKey: 'point_zone_outbound',
    aliases: ['shipping', 'delivery', '出库', '搬出', '9,6']
  },
  {
    id: 'storage_c1',
    x: 3,
    y: 2,
    nameKey: 'point_name_storage_c1',
    zoneKey: 'point_zone_storage',
    aliases: ['rack', 'buffer', '存储', '保管', '3,2']
  },
  {
    id: 'storage_c2',
    x: 3,
    y: 5,
    nameKey: 'point_name_storage_c2',
    zoneKey: 'point_zone_storage',
    aliases: ['rack', 'buffer', '存储', '保管', '3,5']
  },
  {
    id: 'assembly_1',
    x: 6,
    y: 2,
    nameKey: 'point_name_assembly_1',
    zoneKey: 'point_zone_assembly',
    aliases: ['station', 'line', '装配', '组立', '6,2']
  },
  {
    id: 'assembly_2',
    x: 6,
    y: 5,
    nameKey: 'point_name_assembly_2',
    zoneKey: 'point_zone_assembly',
    aliases: ['station', 'line', '装配', '组立', '6,5']
  },
  {
    id: 'charge',
    x: 1,
    y: 7,
    nameKey: 'point_name_charge',
    zoneKey: 'point_zone_service',
    aliases: ['charger', 'battery', '充电', '充電', '1,7']
  },
  {
    id: 'maintenance',
    x: 8,
    y: 7,
    nameKey: 'point_name_maintenance',
    zoneKey: 'point_zone_service',
    aliases: ['repair', 'service', '维护', '保守', '8,7']
  }
]

function getDefaultPointById(id) {
  return DEFAULT_POINT_LIBRARY.find(point => point.id === id)
}

export const DEFAULT_TASK_TEMPLATES = [
  {
    id: 'template_inbound_a_to_storage_c1',
    nameKey: 'template_name_inbound_a_to_storage_c1',
    start_x: getDefaultPointById('inbound_a').x,
    start_y: getDefaultPointById('inbound_a').y,
    end_x: getDefaultPointById('storage_c1').x,
    end_y: getDefaultPointById('storage_c1').y,
    priority: 3,
    custom: false
  },
  {
    id: 'template_inbound_b_to_storage_c2',
    nameKey: 'template_name_inbound_b_to_storage_c2',
    start_x: getDefaultPointById('inbound_b').x,
    start_y: getDefaultPointById('inbound_b').y,
    end_x: getDefaultPointById('storage_c2').x,
    end_y: getDefaultPointById('storage_c2').y,
    priority: 3,
    custom: false
  },
  {
    id: 'template_storage_c1_to_assembly_1',
    nameKey: 'template_name_storage_c1_to_assembly_1',
    start_x: getDefaultPointById('storage_c1').x,
    start_y: getDefaultPointById('storage_c1').y,
    end_x: getDefaultPointById('assembly_1').x,
    end_y: getDefaultPointById('assembly_1').y,
    priority: 4,
    custom: false
  },
  {
    id: 'template_assembly_1_to_outbound_a',
    nameKey: 'template_name_assembly_1_to_outbound_a',
    start_x: getDefaultPointById('assembly_1').x,
    start_y: getDefaultPointById('assembly_1').y,
    end_x: getDefaultPointById('outbound_a').x,
    end_y: getDefaultPointById('outbound_a').y,
    priority: 5,
    custom: false
  }
]
