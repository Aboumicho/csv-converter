"""
comparison package
==================
Compares a pre-surgery fit-check (MicronMapper CSV) against a post-op
TransformedPoints (.txt) file and generates a movement report.

Public API
----------
  MicronMapperCSVReader, ImplantPoint
  match_implants, MatchedPair, gap_sequences
  register_and_compute_deltas, AlignedPoint
  ComparisonReportWriter
  ComparisonPipeline
"""

from comparison.csv_reader import MicronMapperCSVReader, ImplantPoint
from comparison.matcher import match_implants, MatchedPair, gap_sequences
from comparison.registrar import register_and_compute_deltas, AlignedPoint
from comparison.report_writer import ComparisonReportWriter
from comparison.pipeline import ComparisonPipeline

__all__ = [
    "MicronMapperCSVReader",
    "ImplantPoint",
    "match_implants",
    "MatchedPair",
    "gap_sequences",
    "register_and_compute_deltas",
    "AlignedPoint",
    "ComparisonReportWriter",
    "ComparisonPipeline",
]
