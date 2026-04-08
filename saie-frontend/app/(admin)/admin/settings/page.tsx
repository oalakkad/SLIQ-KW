"use client";

import { useRef, useState, useEffect } from "react";
import {
  Box,
  Button,
  FormControl,
  FormLabel,
  Textarea,
  VStack,
  Heading,
  Image,
  Text,
  Spinner,
  useToast,
  HStack,
  Input,
} from "@chakra-ui/react";
import { useSiteSettings, useUpdateSiteSettings } from "@/hooks/use-site-settings";

export default function SettingsPage() {
  const toast = useToast();
  const { data: settings, isLoading } = useSiteSettings();
  const updateSettings = useUpdateSiteSettings();

  const [bioEn, setBioEn] = useState("");
  const [bioAr, setBioAr] = useState("");
  const [logoPreview, setLogoPreview] = useState<string | null>(null);
  const [logoFile, setLogoFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (settings) {
      setBioEn(settings.bio_en);
      setBioAr(settings.bio_ar);
      setLogoPreview(settings.logo || null);
    }
  }, [settings]);

  const handleLogoChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setLogoFile(file);
    setLogoPreview(URL.createObjectURL(file));
  };

  const handleSave = () => {
    const formData = new FormData();
    formData.append("bio_en", bioEn);
    formData.append("bio_ar", bioAr);
    if (logoFile) {
      formData.append("logo", logoFile);
    }

    updateSettings.mutate(formData, {
      onSuccess: () => {
        setLogoFile(null);
        toast({ title: "Settings saved.", status: "success", duration: 3000, isClosable: true });
      },
      onError: () => {
        toast({ title: "Failed to save settings.", status: "error", duration: 3000, isClosable: true });
      },
    });
  };

  if (isLoading) {
    return (
      <Box p={8} display="flex" justifyContent="center">
        <Spinner size="xl" />
      </Box>
    );
  }

  return (
    <Box p={8} maxW="640px">
      <Heading size="md" mb={6} fontFamily="Montserrat, sans-serif">
        Site Settings
      </Heading>

      <VStack spacing={6} align="stretch">
        {/* Logo */}
        <FormControl>
          <FormLabel fontWeight="semibold">Website Logo</FormLabel>
          {logoPreview && (
            <Box mb={3} p={3} border="1px solid" borderColor="gray.200" borderRadius="md" display="inline-block" bg="gray.50">
              <Image src={logoPreview} alt="Site logo" maxH="80px" objectFit="contain" />
            </Box>
          )}
          {!logoPreview && (
            <Box mb={3}>
              <Text fontSize="sm" color="gray.500">No logo uploaded yet.</Text>
            </Box>
          )}
          <Input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            display="none"
            onChange={handleLogoChange}
          />
          <HStack>
            <Button
              size="sm"
              variant="outline"
              onClick={() => fileInputRef.current?.click()}
            >
              {logoPreview ? "Change Logo" : "Upload Logo"}
            </Button>
            {logoFile && (
              <Text fontSize="sm" color="gray.500">{logoFile.name}</Text>
            )}
          </HStack>
        </FormControl>

        {/* Bio EN */}
        <FormControl>
          <FormLabel fontWeight="semibold">About Us — English</FormLabel>
          <Textarea
            value={bioEn}
            onChange={(e) => setBioEn(e.target.value)}
            rows={4}
            placeholder="Write the brand bio in English..."
            fontFamily="Montserrat, sans-serif"
          />
        </FormControl>

        {/* Bio AR */}
        <FormControl>
          <FormLabel fontWeight="semibold">About Us — Arabic</FormLabel>
          <Textarea
            value={bioAr}
            onChange={(e) => setBioAr(e.target.value)}
            rows={4}
            dir="rtl"
            placeholder="اكتب وصف العلامة التجارية بالعربي..."
            fontFamily="Cairo, sans-serif"
          />
        </FormControl>

        <Button
          colorScheme="blue"
          onClick={handleSave}
          isLoading={updateSettings.isPending}
          alignSelf="flex-start"
          px={8}
        >
          Save Changes
        </Button>
      </VStack>
    </Box>
  );
}
