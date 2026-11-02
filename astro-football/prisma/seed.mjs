// Seed reference data: national/club founding charts, venues, Wikipedia aliases, settings.
// Founding data are conventional/commonly cited dates - verify against your sources (Settings page).
import { PrismaClient } from "@prisma/client";

const prisma = new PrismaClient();
const V = "conventional chart - verify";

// [name, type, date, time|null, place, lat, long, tz, defaultVenue, notes]
const TEAMS = [
  ["England", "nation", "1066-12-25", "12:00", "Westminster, London", 51.4995, -0.1273, "Europe/London", "Wembley Stadium", "Coronation of William I (noon chart, Julian date) - " + V],
  ["Brazil", "nation", "1822-09-07", "16:30", "Ipiranga, São Paulo", -23.587, -46.609, "America/Sao_Paulo", null, "Cry of Ipiranga - " + V],
  ["Germany", "nation", "1871-01-18", "12:00", "Versailles", 48.805, 2.120, "Europe/Paris", null, "Proclamation of the German Empire - " + V],
  ["Italy", "nation", "1861-03-17", null, "Turin", 45.070, 7.687, "Europe/Rome", null, "Proclamation of the Kingdom of Italy - " + V],
  ["Spain", "nation", "1492-01-02", null, "Granada", 37.176, -3.588, "Europe/Madrid", null, "Spec cites 1492 (fall of Granada, Julian date) - " + V],
  ["France", "nation", "0843-08-10", null, "Verdun", 49.160, 5.385, "Europe/Paris", null, "Spec cites 843 (Treaty of Verdun; day uncertain, Julian) - " + V],
  ["Argentina", "nation", "1816-07-09", null, "San Miguel de Tucumán", -26.830, -65.204, "America/Argentina/Tucuman", null, "Declaration of Independence - " + V],
  ["Netherlands", "nation", "1581-07-26", null, "The Hague", 52.078, 4.288, "Europe/Amsterdam", null, "Act of Abjuration (Julian date) - " + V],
  ["Portugal", "nation", "1143-10-05", null, "Zamora", 41.503, -5.745, "Europe/Madrid", null, "Treaty of Zamora (Julian date) - " + V],
  ["India", "nation", "1947-08-15", "00:00", "New Delhi", 28.614, 77.209, "Asia/Kolkata", "Eden Gardens", "Independence - " + V],
  ["Australia", "nation", "1901-01-01", null, "Sydney", -33.869, 151.209, "Australia/Sydney", null, "Federation - " + V],
  ["New Zealand", "nation", "1907-09-26", null, "Wellington", -41.287, 174.776, "Pacific/Auckland", null, "Dominion status - " + V],
  ["United States", "nation", "1776-07-04", null, "Philadelphia", 39.949, -75.150, "America/New_York", null, "Declaration of Independence (time disputed) - " + V],
  // clubs (founding date only unless noted)
  ["FC Barcelona", "club", "1899-11-29", null, "Barcelona", 41.388, 2.170, "Europe/Madrid", "Camp Nou", V],
  ["Real Madrid", "club", "1902-03-06", null, "Madrid", 40.417, -3.704, "Europe/Madrid", "Santiago Bernabéu", V],
  ["Atlético Madrid", "club", "1903-04-26", null, "Madrid", 40.417, -3.704, "Europe/Madrid", "Metropolitano", V],
  ["Valencia CF", "club", "1919-03-18", null, "Valencia", 39.470, -0.376, "Europe/Madrid", "Mestalla", V],
  ["Sevilla FC", "club", "1890-01-25", null, "Seville", 37.389, -5.984, "Europe/Madrid", "Ramón Sánchez Pizjuán", V],
  ["Bayern München", "club", "1900-02-27", null, "Munich", 48.137, 11.576, "Europe/Berlin", "Allianz Arena", V],
  ["Borussia Dortmund", "club", "1909-12-19", null, "Dortmund", 51.514, 7.465, "Europe/Berlin", "Signal Iduna Park", V],
  ["Juventus", "club", "1897-11-01", null, "Turin", 45.070, 7.687, "Europe/Rome", "Allianz Stadium", V],
  ["AC Milan", "club", "1899-12-16", null, "Milan", 45.464, 9.190, "Europe/Rome", "San Siro", V],
  ["Inter", "club", "1908-03-09", null, "Milan", 45.464, 9.190, "Europe/Rome", "San Siro", V],
  ["SSC Napoli", "club", "1926-08-01", null, "Naples", 40.852, 14.268, "Europe/Rome", "Stadio Diego Armando Maradona", V],
  ["AS Roma", "club", "1927-06-07", null, "Rome", 41.903, 12.496, "Europe/Rome", "Stadio Olimpico", V],
  ["Lazio Roma", "club", "1900-01-09", null, "Rome", 41.903, 12.496, "Europe/Rome", "Stadio Olimpico", V],
  ["Liverpool", "club", "1892-06-03", null, "Liverpool", 53.408, -2.991, "Europe/London", "Anfield", V],
  ["Chelsea", "club", "1905-03-10", null, "London", 51.507, -0.128, "Europe/London", "Stamford Bridge", V],
  ["Tottenham Hotspur", "club", "1882-09-05", null, "London", 51.507, -0.128, "Europe/London", "Tottenham Hotspur Stadium", V],
  ["Manchester United", "club", "1902-04-24", null, "Manchester", 53.481, -2.243, "Europe/London", "Old Trafford", "Renamed from Newton Heath (founded 1878) - " + V],
  ["Manchester City", "club", "1894-04-16", null, "Manchester", 53.481, -2.243, "Europe/London", "Etihad Stadium", "Re-formed as Manchester City (roots 1880) - " + V],
  ["Arsenal", "club", null, null, null, null, null, null, "Emirates Stadium", "Founded 1886 - exact date not recorded here; add it"],
  ["Paris Saint-Germain", "club", "1970-08-12", null, "Paris", 48.857, 2.352, "Europe/Paris", "Parc des Princes", V],
  ["Olympique Marseille", "club", "1899-08-31", null, "Marseille", 43.297, 5.381, "Europe/Paris", "Stade Vélodrome", V],
  ["Ajax", "club", "1900-03-18", null, "Amsterdam", 52.370, 4.895, "Europe/Amsterdam", "Johan Cruyff Arena", V],
  ["Celtic", "club", "1887-11-06", null, "Glasgow", 55.864, -4.252, "Europe/London", "Celtic Park", V],
  ["Benfica", "club", "1904-02-28", null, "Lisbon", 38.722, -9.139, "Europe/Lisbon", "Estádio da Luz", V],
  ["FC Porto", "club", "1893-09-28", null, "Porto", 41.158, -8.629, "Europe/Lisbon", "Estádio do Dragão", V],
  ["Boca Juniors", "club", "1905-04-03", null, "Buenos Aires", -34.604, -58.382, "America/Argentina/Buenos_Aires", "La Bombonera", V],
  ["River Plate", "club", "1901-05-25", null, "Buenos Aires", -34.604, -58.382, "America/Argentina/Buenos_Aires", "Estadio Monumental", V],
];

// [name, lat, long, tz]
const VENUES = [
  ["Arena Fonte Nova", -12.9787, -38.5043, "America/Bahia"], ["Stade Vélodrome", 43.2698, 5.3959, "Europe/Paris"],
  ["Camp Nou", 41.3809, 2.1228, "Europe/Madrid"], ["Emirates Stadium", 51.5549, -0.1084, "Europe/London"],
  ["Old Trafford", 53.4631, -2.2913, "Europe/London"], ["Anfield", 53.4308, -2.9608, "Europe/London"],
  ["Stamford Bridge", 51.4817, -0.1910, "Europe/London"], ["Etihad Stadium", 53.4831, -2.2004, "Europe/London"],
  ["Tottenham Hotspur Stadium", 51.6043, -0.0664, "Europe/London"], ["Wembley Stadium", 51.5560, -0.2796, "Europe/London"],
  ["Santiago Bernabéu", 40.4531, -3.6883, "Europe/Madrid"], ["Metropolitano", 40.4362, -3.5995, "Europe/Madrid"],
  ["Mestalla", 39.4746, -0.3583, "Europe/Madrid"], ["Ramón Sánchez Pizjuán", 37.3840, -5.9705, "Europe/Madrid"],
  ["Allianz Arena", 48.2188, 11.6247, "Europe/Berlin"], ["Signal Iduna Park", 51.4926, 7.4519, "Europe/Berlin"],
  ["Allianz Stadium", 45.1096, 7.6413, "Europe/Rome"], ["San Siro", 45.4781, 9.1240, "Europe/Rome"],
  ["Stadio Olimpico", 41.9341, 12.4547, "Europe/Rome"], ["Stadio Diego Armando Maradona", 40.8280, 14.1931, "Europe/Rome"],
  ["Parc des Princes", 48.8414, 2.2530, "Europe/Paris"], ["Johan Cruyff Arena", 52.3143, 4.9419, "Europe/Amsterdam"],
  ["Celtic Park", 55.8497, -4.2055, "Europe/London"], ["Estádio da Luz", 38.7527, -9.1847, "Europe/Lisbon"],
  ["Estádio do Dragão", 41.1618, -8.5837, "Europe/Lisbon"], ["La Bombonera", -34.6356, -58.3647, "America/Argentina/Buenos_Aires"],
  ["Estadio Monumental", -34.5453, -58.4498, "America/Argentina/Buenos_Aires"], ["Eden Gardens", 22.5646, 88.3433, "Asia/Kolkata"],
];

const ALIASES = [
  ["Old Trafford", "Old Trafford (football)"], ["Camp Nou", "Spotify Camp Nou"], ["Santiago Bernabéu", "Santiago Bernabéu Stadium"],
  ["Allianz Stadium", "Juventus Stadium"], ["Metropolitano", "Metropolitano Stadium"], ["San Siro", "San Siro"],
  ["Stadio Olimpico", "Stadio Olimpico"], ["Arena Fonte Nova", "Arena Fonte Nova"], ["Signal Iduna Park", "Westfalenstadion"],
  ["La Bombonera", "La Bombonera"], ["Estadio Monumental", "Estadio Monumental (Buenos Aires)"], ["Eden Gardens", "Eden Gardens"],
];

async function main() {
  for (const [name, lat, long, tz] of VENUES) {
    await prisma.venue.upsert({ where: { name }, update: {}, create: { name, lat, long, timezone: tz, coordinateSource: "seed", lastVerifiedAt: new Date() } });
  }
  for (const [name, type, date, time, place, lat, long, tz, venue, notes] of TEAMS) {
    const data = {
      displayName: name, nationOrClub: type, foundingDate: date ? new Date(date + "T00:00:00Z") : null, foundingTime: time,
      foundingPlace: place, foundingLat: lat, foundingLong: long, foundingTz: tz, defaultVenue: venue, notes,
    };
    await prisma.team.upsert({ where: { name }, update: {}, create: { name, ...data } });
  }
  for (const [venueName, wikiTitle] of ALIASES) {
    await prisma.wikiAlias.upsert({ where: { venueName }, update: {}, create: { venueName, wikiTitle } });
  }
  console.log(`seeded ${TEAMS.length} teams, ${VENUES.length} venues, ${ALIASES.length} Wikipedia aliases`);
}

main().finally(() => prisma.$disconnect());
