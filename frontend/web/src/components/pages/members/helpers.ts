export const getEnrolmentStatusType = (status?: string): 'error' | 'pending' | 'success' => {
  switch (status) {
    case 'Approved':
      return 'success';
    case 'Rejected':
      return 'error';
    case 'Pending':
      return 'pending';
    default:
      return 'pending';
  }
};
