export const BUYER = "Mike's Motors (Rochester)"
export const SELLER = "Sarah's Truck Center (Buffalo)"

export const PITCH = 'Need 5 Camrys, 2018+, under $12K, clean title, delivered to Rochester by Friday.'
export const SUGGESTIONS = [
  PITCH,
  'Need 2 Accords 2017 or newer under 14k delivered to Toledo',
  'Need 4 RAV4s under 20k to Albany',
]

export const MODELS = [
  'Toyota Camry', 'Toyota Corolla', 'Toyota RAV4', 'Toyota Tacoma', 'Toyota Highlander', 'Honda Civic', 'Honda Accord',
  'Honda CR-V', 'Ford F-150', 'Ford Escape', 'Ford Explorer', 'Chevrolet Silverado 1500', 'Chevrolet Equinox',
  'Chevrolet Malibu', 'Ram 1500', 'Nissan Altima', 'Nissan Rogue', 'Hyundai Elantra', 'Hyundai Tucson',
  'Jeep Grand Cherokee', 'Jeep Wrangler', 'Subaru Outback', 'Tesla Model 3',
]
export const MAKES = ['Toyota', 'Honda', 'Ford', 'Chevrolet', 'Ram', 'Nissan', 'Hyundai', 'Jeep', 'Subaru', 'Tesla']
export const splitModel = (label) => {
  const make = MAKES.find((m) => label.startsWith(m + ' '))
  return [make, label.slice(make.length + 1)]
}

export const CITIES = ['Buffalo', 'Rochester', 'Syracuse', 'Albany', 'Binghamton', 'New York', 'Erie', 'Pittsburgh',
  'Scranton', 'Harrisburg', 'Philadelphia', 'Cleveland', 'Akron', 'Columbus', 'Toledo', 'Detroit']
export const COLORS = ['Silver', 'White', 'Black', 'Gray', 'Blue', 'Red']
export const FLEET_MODELS = [['Nissan', 'Altima'], ['Toyota', 'Corolla'], ['Chevrolet', 'Malibu']]
