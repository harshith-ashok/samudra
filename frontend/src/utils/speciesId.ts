// Mirrors services/trajectory.py's species_id() so the frontend can derive the
// same slug from a scientific name without a round trip to the backend.
export function speciesSlug(scientificName: string): string {
  return scientificName.trim().toLowerCase().replace(/\s+/g, "_");
}
