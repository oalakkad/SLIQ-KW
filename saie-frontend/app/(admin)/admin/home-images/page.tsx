"use client";

import { useRef, useState } from "react";
import {
  Box,
  Heading,
  SimpleGrid,
  VStack,
  Text,
  Image,
  Button,
  Input,
  Spinner,
  useToast,
  Badge,
} from "@chakra-ui/react";
import { useHomeImages, useUpdateHomeImage } from "@/hooks/use-home-images";

const HOME_IMAGE_SLOTS = [
  { key: "home-1", label: "Hair Clips — Image 1" },
  { key: "home-2", label: "Hair Clips — Image 2" },
  { key: "home-3", label: "Hair Clips — Image 3" },
  { key: "home-4", label: "Hair Brushes — Image 1" },
  { key: "home-5", label: "Hair Brushes — Image 2" },
  { key: "home-6", label: "Hair Brushes — Image 3" },
  { key: "home-7", label: "Makeup Bags — Image 1" },
  { key: "home-8", label: "Makeup Bags — Image 2" },
  { key: "home-9", label: "Makeup Bags — Image 3" },
  { key: "banner", label: "Inspired By Banner" },
  { key: "banner2", label: "About Us Banner" },
  { key: "category-hair-clips", label: "Category Card — Hair Clips" },
  { key: "category-hair-brushes", label: "Category Card — Hair Brushes" },
  { key: "category-premade-clips", label: "Category Card — Pre-Made Clips" },
  { key: "category-makeup-bags", label: "Category Card — Makeup Bags" },
];

function ImageSlot({ slotKey, label, currentImage }: { slotKey: string; label: string; currentImage: string | null }) {
  const toast = useToast();
  const inputRef = useRef<HTMLInputElement>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const updateImage = useUpdateHomeImage();

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (!f) return;
    setFile(f);
    setPreview(URL.createObjectURL(f));
  };

  const handleUpload = () => {
    if (!file) return;
    const formData = new FormData();
    formData.append("image", file);
    updateImage.mutate(
      { key: slotKey, formData },
      {
        onSuccess: () => {
          toast({ title: "Image updated!", status: "success", duration: 3000, isClosable: true });
          setFile(null);
          setPreview(null);
        },
        onError: () => {
          toast({ title: "Failed to update image.", status: "error", duration: 3000, isClosable: true });
        },
      }
    );
  };

  const displayImage = preview || currentImage;

  return (
    <VStack
      align="stretch"
      border="1px solid"
      borderColor="gray.200"
      borderRadius="md"
      p={4}
      spacing={3}
      bg="gray.50"
    >
      <Text fontWeight="semibold" fontSize="sm">{label}</Text>
      {displayImage ? (
        <Image
          src={displayImage}
          alt={label}
          h="150px"
          objectFit="cover"
          borderRadius="md"
          border="1px solid"
          borderColor="gray.200"
        />
      ) : (
        <Box
          h="150px"
          bg="gray.100"
          borderRadius="md"
          display="flex"
          alignItems="center"
          justifyContent="center"
        >
          <Text fontSize="xs" color="gray.400">No image</Text>
        </Box>
      )}
      {preview && (
        <Badge colorScheme="orange" alignSelf="center">New — not saved yet</Badge>
      )}
      <Input
        ref={inputRef}
        type="file"
        accept="image/*"
        display="none"
        onChange={handleFileChange}
      />
      <Button size="sm" variant="outline" onClick={() => inputRef.current?.click()}>
        Choose Image
      </Button>
      {file && (
        <Button
          size="sm"
          colorScheme="blue"
          onClick={handleUpload}
          isLoading={updateImage.isPending}
        >
          Upload
        </Button>
      )}
    </VStack>
  );
}

export default function HomeImagesPage() {
  const { data: homeImages, isLoading } = useHomeImages();

  const getImageUrl = (key: string) =>
    homeImages?.find((img) => img.key === key)?.image || null;

  if (isLoading) {
    return (
      <Box p={8} display="flex" justifyContent="center">
        <Spinner size="xl" />
      </Box>
    );
  }

  return (
    <Box p={8}>
      <Heading size="md" mb={2} fontFamily="Montserrat, sans-serif">
        Home Images
      </Heading>
      <Text fontSize="sm" color="gray.500" mb={6}>
        Upload images for each section of the homepage. Changes go live immediately after upload.
      </Text>
      <SimpleGrid columns={{ base: 1, md: 3, lg: 4 }} gap={6}>
        {HOME_IMAGE_SLOTS.map((slot) => (
          <ImageSlot
            key={slot.key}
            slotKey={slot.key}
            label={slot.label}
            currentImage={getImageUrl(slot.key)}
          />
        ))}
      </SimpleGrid>
    </Box>
  );
}
