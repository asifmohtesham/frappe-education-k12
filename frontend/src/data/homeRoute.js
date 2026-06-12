export function homeRouteFor(context) {
  if (context?.is_teacher) return 'TeacherHomerooms'
  if (context?.is_guardian) return 'Children'
  return 'NoAccess'
}
