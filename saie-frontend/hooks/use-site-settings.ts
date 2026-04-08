import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/components/utils/api";

export interface SiteSettings {
  id: number;
  logo: string | null;
  bio_en: string;
  bio_ar: string;
}

const fetchSiteSettings = async (): Promise<SiteSettings> => {
  const { data } = await api.get<SiteSettings>("/site-settings/");
  return data;
};

export const useSiteSettings = () => {
  return useQuery<SiteSettings, Error>({
    queryKey: ["siteSettings"],
    queryFn: fetchSiteSettings,
    staleTime: 5 * 60_000,
    refetchOnWindowFocus: false,
    retry: 1,
  });
};

export const useUpdateSiteSettings = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (formData: FormData) =>
      api.patch<SiteSettings>("/site-settings/", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      }).then((r) => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["siteSettings"] });
    },
  });
};
