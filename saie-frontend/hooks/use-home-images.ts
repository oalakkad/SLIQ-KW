import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/components/utils/api";

export interface HomeImage {
  id: number;
  key: string;
  label: string;
  image: string | null;
}

const fetchHomeImages = async (): Promise<HomeImage[]> => {
  const { data } = await api.get<HomeImage[] | { results: HomeImage[] }>("/home-images/");
  return Array.isArray(data) ? data : data.results;
};

export const useHomeImages = () => {
  return useQuery<HomeImage[], Error>({
    queryKey: ["homeImages"],
    queryFn: fetchHomeImages,
    staleTime: 5 * 60_000,
    refetchOnWindowFocus: false,
    retry: 1,
  });
};

export const useUpdateHomeImage = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ key, formData }: { key: string; formData: FormData }) =>
      api.patch<HomeImage>(`/home-images/${key}/`, formData).then((r) => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["homeImages"] });
    },
  });
};
