export const PROGRAM_OPTIONS = [
  "B.Tech (CSE)",
  "B.Tech (AI & ML)",
  "B.Tech (AI & DS)",
  "M.Tech",
  "BCA",
  "MCA",
  "Diploma",
] as const;

export const YEAR_OF_STUDY_OPTIONS = [
  "1st Year",
  "2nd Year",
  "3rd Year",
  "4th Year",
  "5th Year",
] as const;

export const SEMESTER_OPTIONS = Array.from(
  { length: 10 },
  (_, index) => `Semester ${index + 1}`,
);
