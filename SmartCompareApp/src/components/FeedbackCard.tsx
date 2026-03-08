/**
 * FeedbackCard - Inline feedback collection shown below comparison results
 */
import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  TextInput,
} from 'react-native';
import { submitFeedback } from '../services/api';

const MATTERED_OPTIONS = [
  'price', 'specs', 'reviews', 'brand', 'value', 'ratings',
] as const;

interface FeedbackCardProps {
  comparisonId?: string;
}

export default function FeedbackCard({ comparisonId }: FeedbackCardProps) {
  const [useful, setUseful] = useState<boolean | null>(null);
  const [matteredMost, setMatteredMost] = useState<string[]>([]);
  const [suggestion, setSuggestion] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  if (submitted) {
    return (
      <View style={styles.card}>
        <Text style={styles.thanksText}>Thanks for your feedback!</Text>
      </View>
    );
  }

  const toggleMattered = (item: string) => {
    setMatteredMost((prev) =>
      prev.includes(item) ? prev.filter((i) => i !== item) : [...prev, item]
    );
  };

  const handleSubmit = async () => {
    if (useful === null) return;
    setSubmitting(true);
    try {
      await submitFeedback({
        useful,
        comparison_id: comparisonId,
        mattered_most: matteredMost,
        change_suggestion: suggestion.trim() || undefined,
      });
    } catch {
      // Fire-and-forget — don't block UI on failure
    }
    setSubmitted(true);
    setSubmitting(false);
  };

  return (
    <View style={styles.card}>
      <Text style={styles.title}>Was this comparison useful?</Text>

      {/* Thumbs up/down */}
      <View style={styles.thumbsRow}>
        <TouchableOpacity
          style={[styles.thumbButton, useful === true && styles.thumbSelected]}
          onPress={() => setUseful(true)}
        >
          <Text style={styles.thumbText}>Yes</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.thumbButton, useful === false && styles.thumbSelectedNo]}
          onPress={() => setUseful(false)}
        >
          <Text style={styles.thumbText}>No</Text>
        </TouchableOpacity>
      </View>

      {/* Mattered most chips (optional) */}
      {useful !== null && (
        <>
          <Text style={styles.subLabel}>What mattered most? (optional)</Text>
          <View style={styles.chipsRow}>
            {MATTERED_OPTIONS.map((item) => (
              <TouchableOpacity
                key={item}
                style={[styles.chip, matteredMost.includes(item) && styles.chipSelected]}
                onPress={() => toggleMattered(item)}
              >
                <Text
                  style={[styles.chipText, matteredMost.includes(item) && styles.chipTextSelected]}
                >
                  {item.charAt(0).toUpperCase() + item.slice(1)}
                </Text>
              </TouchableOpacity>
            ))}
          </View>

          {/* Optional text input */}
          <Text style={styles.subLabel}>Anything to improve? (optional)</Text>
          <TextInput
            style={styles.textInput}
            placeholder="Tell us what could be better..."
            placeholderTextColor="#999"
            value={suggestion}
            onChangeText={setSuggestion}
            multiline
            maxLength={500}
          />

          {/* Submit */}
          <TouchableOpacity
            style={[styles.submitButton, submitting && styles.submitDisabled]}
            onPress={handleSubmit}
            disabled={submitting}
          >
            <Text style={styles.submitText}>
              {submitting ? 'Sending...' : 'Submit Feedback'}
            </Text>
          </TouchableOpacity>
        </>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: '#FFF',
    margin: 10,
    padding: 15,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#E0E0E0',
  },
  title: {
    fontSize: 15,
    fontWeight: '600',
    color: '#333',
    marginBottom: 12,
  },
  thumbsRow: {
    flexDirection: 'row',
    gap: 10,
    marginBottom: 12,
  },
  thumbButton: {
    flex: 1,
    paddingVertical: 10,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#E0E0E0',
    alignItems: 'center',
  },
  thumbSelected: {
    backgroundColor: '#E8F5E9',
    borderColor: '#4CAF50',
  },
  thumbSelectedNo: {
    backgroundColor: '#FFEBEE',
    borderColor: '#F44336',
  },
  thumbText: {
    fontSize: 14,
    fontWeight: '500',
    color: '#333',
  },
  subLabel: {
    fontSize: 13,
    color: '#666',
    marginBottom: 8,
  },
  chipsRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
    marginBottom: 12,
  },
  chip: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: '#E0E0E0',
    backgroundColor: '#FAFAFA',
  },
  chipSelected: {
    backgroundColor: '#E3F2FD',
    borderColor: '#2196F3',
  },
  chipText: {
    fontSize: 12,
    color: '#666',
  },
  chipTextSelected: {
    color: '#2196F3',
    fontWeight: '600',
  },
  textInput: {
    backgroundColor: '#F5F5F5',
    borderRadius: 8,
    padding: 10,
    fontSize: 13,
    color: '#333',
    marginBottom: 12,
    minHeight: 60,
    textAlignVertical: 'top',
    borderWidth: 1,
    borderColor: '#E0E0E0',
  },
  submitButton: {
    backgroundColor: '#2196F3',
    paddingVertical: 10,
    borderRadius: 8,
    alignItems: 'center',
  },
  submitDisabled: {
    opacity: 0.6,
  },
  submitText: {
    color: '#FFF',
    fontSize: 14,
    fontWeight: '600',
  },
  thanksText: {
    fontSize: 14,
    color: '#4CAF50',
    fontWeight: '500',
    textAlign: 'center',
  },
});
