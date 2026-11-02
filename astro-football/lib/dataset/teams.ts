// Normalises a Team form payload (Settings page) into Prisma data.
export function teamData(b: any) {
  return {
    name: b.name, displayName: b.displayName || b.name, nationOrClub: b.nationOrClub || "club",
    foundingDate: b.foundingDate ? new Date(String(b.foundingDate).slice(0, 10) + "T00:00:00Z") : null,
    foundingTime: b.foundingTime || null, foundingPlace: b.foundingPlace || null,
    foundingLat: b.foundingLat === "" || b.foundingLat == null ? null : Number(b.foundingLat),
    foundingLong: b.foundingLong === "" || b.foundingLong == null ? null : Number(b.foundingLong),
    foundingTz: b.foundingTz || null, defaultVenue: b.defaultVenue || null, notes: b.notes || null,
  };
}
