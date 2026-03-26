interface UserDateProps {
  date: string | Date | undefined,
}

export const UserDate = ({ date }: UserDateProps) => {
  if (date === undefined) {
    return <></>;
  }
  if (typeof date === 'string') {
    return <>{new Date(date).toLocaleString()}</>;
  }
  if (date instanceof Date) {
    return <>{date.toLocaleString()}</>;
  }
  return <>{date}</>;
};