import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
from PIL import Image
import numpy as np
import os

def _add_image_annotation(ax, x, y, image_path, xybox_offset):
    """
    Helper function to add an image annotation to a matplotlib axis.
    """
    if not image_path or not os.path.exists(image_path):
        return

    try:
        # Load and resize image to prevent excessive scale issues while maintaining aspect ratio
        img = Image.open(image_path)
        img.thumbnail((200, 200))
        img_arr = np.array(img)
        
        # Create OffsetImage
        imagebox = OffsetImage(img_arr, zoom=0.3)
        imagebox.image.axes = ax
        
        # Add to plot with specific offset
        ab = AnnotationBbox(imagebox, (x, y),
                            xybox=xybox_offset,
                            xycoords='data',
                            boxcoords="offset points",
                            pad=0.1,
                            frameon=False)
        ax.add_artist(ab)
    except Exception as e:
        print(f"Error loading image '{image_path}': {e}")


def generate_cgpa_comparison(student_cgpa, dept_avg, photo_path=None, output_filename="cgpa_comparison.png"):
    """
    Generates a bar graph comparing Student CGPA with Department Average CGPA.
    """
    # Apply professional seaborn styling
    sns.set_theme(style="whitegrid", context="talk")
    fig, ax = plt.subplots(figsize=(8, 6))

    # Data
    labels = ['Student CGPA', 'Department Avg']
    values = [student_cgpa, dept_avg]
    colors = sns.color_palette("deep", 2)

    # Plot vertical bars
    bars = ax.bar(labels, values, color=colors, width=0.5)

    # Styling and limits
    ax.set_ylim(0, 10)
    ax.set_yticks(np.arange(0, 11, 1))
    ax.set_ylabel("CGPA Score", fontweight='bold')
    ax.set_title("CGPA Comparison", fontsize=16, fontweight='bold', pad=20)
    
    # Add text labels on bars
    for i, bar in enumerate(bars):
        height = bar.get_height()
        # Leave extra vertical space for the text if it's the student bar and a photo is present
        text_y_offset = 55 if (i == 0 and photo_path and os.path.exists(photo_path)) else 8
        
        ax.annotate(f'{height:.2f}',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, text_y_offset),
                    textcoords="offset points",
                    ha='center', va='bottom', fontsize=12, fontweight='bold')

    # Add student photo above their bar
    if photo_path and os.path.exists(photo_path):
        _add_image_annotation(
            ax, 
            x=bars[0].get_x() + bars[0].get_width() / 2, 
            y=student_cgpa, 
            image_path=photo_path, 
            xybox_offset=(0, 30)
        )

    plt.tight_layout()
    plt.savefig(output_filename, dpi=300)
    plt.close()


def generate_employability_graph(student_score, dept_avg_score, photo_path=None, output_filename="employability_score.png"):
    """
    Generates a horizontal progress-style graph comparing Employability Score.
    """
    # Apply seaborn styling
    sns.set_theme(style="whitegrid", context="talk")
    fig, ax = plt.subplots(figsize=(10, 4))

    # Data (Student placed on top for emphasis)
    labels = ['Department Avg', 'Student Score']  
    values = [dept_avg_score, student_score]
    
    # Highlight student score with a distinct color (Green for student, Gray for average)
    colors = [sns.color_palette("muted")[7], sns.color_palette("bright")[2]] 

    # Plot horizontal bars
    bars = ax.barh(labels, values, color=colors, height=0.5)

    # Styling and limits
    ax.set_xlim(0, 100)
    ax.set_xlabel("Employability Score (0-100)", fontweight='bold')
    ax.set_title("Employability Evaluation", fontsize=16, fontweight='bold', pad=20)
    
    # Add text labels at the end of bars
    for i, bar in enumerate(bars):
        width = bar.get_width()
        # Leave extra horizontal space if it's the student bar and an image is provided
        text_x_offset = 65 if (i == 1 and photo_path and os.path.exists(photo_path)) else 10
        
        ax.annotate(f'{width:.1f}',
                    xy=(width, bar.get_y() + bar.get_height() / 2),
                    xytext=(text_x_offset, 0),
                    textcoords="offset points",
                    ha='left', va='center', fontsize=12, fontweight='bold')

    # Add student photo near their bar
    if photo_path and os.path.exists(photo_path):
        _add_image_annotation(
            ax, 
            x=student_score, 
            y=bars[1].get_y() + bars[1].get_height() / 2, 
            image_path=photo_path, 
            xybox_offset=(35, 0)
        )

    plt.tight_layout()
    plt.savefig(output_filename, dpi=300)
    plt.close()
