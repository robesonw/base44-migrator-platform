import { useQuery } from '@tanstack/react-query';

export default function Community() {
  const { data: sharedPlans = [] } = useQuery({
    queryKey: ['sharedPlans'],
    queryFn: fetchSharedPlans,
  });

  return (
    <div>
      {/* Render community features and stats here */}
    </div>
  );
}

async function fetchSharedPlans() {
  const response = await fetch('/api/sharedPlans');
  return response.json();
}